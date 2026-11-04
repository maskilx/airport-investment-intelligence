"""FAA sources: ACAIS enplanement / all-cargo workbooks and the Terminal Area Forecast."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import openpyxl

from ..rawstore import RawFile, Vintage
from ..validation import error, scalar, warning
from .base import FetchResult, Source, TableSpec, rows_to_table, snake

FAA = "https://www.faa.gov"
ACAIS_PAGES = (FAA + "/airports/planning_capacity/passenger_allcargo_stats/passenger",
               FAA + "/airports/planning_capacity/passenger_allcargo_stats/passenger/previous_years")


def _xlsx_rows(path: Path, header_hint: str):
    """Yield (header, rows) from the first sheet, locating the header row by a hint cell."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    for row in it:
        if row and any(isinstance(c, str) and c.strip().lower() == header_hint.lower() for c in row):
            header = [str(c).strip() if c is not None else "" for c in row]
            break
    else:
        raise ValueError(f"{path.name}: header row with {header_hint!r} not found")
    keep = [i for i, h in enumerate(header) if h]
    rows = (tuple(r[i] if i < len(r) else None for i in keep) for r in it if r and any(c is not None for c in r))
    return [header[i] for i in keep], rows


# ------------------------------------------------------------------ ACAIS
class AcaisWorkbook(Source):
    """FAA CY 'Passenger Boarding (Enplanement) and All-Cargo Data' workbooks.

    `kind` selects the workbook family; one class serves both so new FAA
    workbook families can be added by instantiation, not new code."""
    publisher = "Federal Aviation Administration (ACAIS)"
    license = "U.S. Government work — public domain"
    homepage = ACAIS_PAGES[0]
    period_kind = "year"
    cadence = "annual"
    expected_lag_days = 300  # CY data published ~Q3/Q4 of the following year
    # header spellings differ across years/workbooks -> one canonical name
    ALIASES = {"faa_region": "ro", "svc_lvl": "s_l", "arpt_category": "s_l", "service_level": "s_l", "s_l": "s_l", "airport_name": "airport_name"}

    def __init__(self, kind: str):
        self.kind = kind
        if kind == "commercial-service-enplanements":
            self.id, self.title = "faa_enplanements", "FAA CY commercial-service enplanements (boardings) by airport"
            tname, desc = "faa_enplanements", "One row per commercial-service airport per CY workbook."
            self.notes = ("Revenue enplanements (ACAIS), basis of hub classification and AIP entitlements. Not "
                          "comparable 1:1 with T-100 segment passengers (through pax, transit-passenger rules).")
        elif kind == "all-cargo-airports":
            self.id, self.title = "faa_cargo", "FAA CY all-cargo landed weight by airport"
            tname, desc = "faa_cargo", "One row per qualifying all-cargo airport per CY workbook."
            self.notes = "All-cargo aircraft landed weight (lbs), airports with >100M lbs."
        else:
            raise ValueError(kind)
        self.tables = (TableSpec(name=tname, description=desc,
                                 required_columns=("cy", "locid", "st", "hub", "s_l", "value_cy", "value_prior_cy"),
                                 not_null=("cy", "locid"), unique_key=("cy", "locid"), unique_key_blocking=True,
                                 min_rows=50,
                                 placeholder_types=(("cy", "INTEGER"), ("value_cy", "DOUBLE"), ("value_prior_cy", "DOUBLE"))),)

    def _links(self, http) -> dict[str, str]:
        out: dict[str, str] = {}
        for page in ACAIS_PAGES:
            for href in re.findall(r'href="([^"]+\.xlsx)"', http.get(page).text):
                name = href.rsplit("/", 1)[-1].lower()
                m = re.search(r"cy[-_ ]?(\d{2,4})", name)
                if m and self.kind.split("-")[0] in name and ("cargo" in name) == ("cargo" in self.kind):
                    y = int(m.group(1))
                    out[str(y + 2000 if y < 100 else y)] = href if href.startswith("http") else FAA + href
        return out

    def available_periods(self, http) -> list[str]:
        return sorted(self._links(http))

    def fetch(self, period, http) -> FetchResult:
        url = self._links(http)[period]
        r = http.get(url)
        return FetchResult([RawFile(url.rsplit("/", 1)[-1], r.body)], url, {"method": "GET"},
                           {k: r.headers[k] for k in ("content-type", "content-length", "last-modified", "etag") if k in r.headers})

    def load(self, con, v, staging, tmp):
        header, rows = _xlsx_rows(v.file(v.files[0]["name"]), "Locid")
        names, seen_cy, measure = [], 0, None
        for h in header:
            # "CY 25 Enplanements" | "2025 Landed\nWeight (lbs.)" -> first = current CY, second = prior CY
            m = re.match(r"(?:CY\s*)?(\d{2}|\d{4})\s+(.+)", h.replace("\n", " "), re.I)
            if m:
                names.append("value_cy" if seen_cy == 0 else "value_prior_cy")
                if seen_cy == 0:
                    measure = snake(m.group(2))
                seen_cy += 1
            elif h.strip().startswith("%"):
                names.append("pct_change")
            else:
                names.append(self.ALIASES.get(snake(h), snake(h)))
        if seen_cy != 2:
            raise ValueError(f"expected 2 CY value columns, found {seen_cy} in header {header}")
        t = staging[self.tables[0].name]
        rows_to_table(con, t, names, rows, tmp, types={"locid": "VARCHAR", "value_cy": "DOUBLE", "value_prior_cy": "DOUBLE"})
        con.execute(f'ALTER TABLE "{t}" ADD COLUMN cy INTEGER DEFAULT {int(v.period)}')
        con.execute(f'ALTER TABLE "{t}" ADD COLUMN measure VARCHAR DEFAULT \'{measure}\'')
        # drop footer/total rows (no locid)
        con.execute(f'DELETE FROM "{t}" WHERE locid IS NULL OR trim(locid) = \'\'')

    def checks(self, con, v, staging):
        t = staging[self.tables[0].name]
        neg = scalar(con, f'SELECT count(*) FROM "{t}" WHERE value_cy < 0 OR value_prior_cy < 0')
        yield error("non_negative_values", neg == 0, f"{neg} negative values", value=neg)


# ------------------------------------------------------------------ TAF
TAF_FILES = {  # workbook -> (table, description)
    "Airports.xlsx": ("taf_airport", "TAF airport attributes (LOCID, region, hub size, ATCT flag, ...)"),
    "AirportsOperations.xlsx": ("taf_operations", "Operations by fiscal year: itinerant/local by user class"),
    "Enplanements.xlsx": ("taf_enplanements", "Enplanements by fiscal year: air carrier, commuter, US/foreign flag"),
    "BasedAircraft.xlsx": ("taf_based_aircraft", "Based aircraft by fiscal year"),
    "Tracon.xlsx": ("taf_tracon", "TRACON operations by fiscal year"),
}

TAF_REQUIRED = {
    "taf_airport": ("locid", "region", "state", "hub_size", "atct_flag"),
    "taf_operations": ("locid", "scenario", "fiscal_year", "itn_ac", "itn_at", "itn_ga", "itn_mil", "loc_ga", "loc_mil"),
    "taf_enplanements": ("locid", "scenario", "fiscal_year", "aac", "aat", "commuter", "us_flag", "frgn_flag"),
    "taf_based_aircraft": ("locid", "scenario", "fiscal_year"),
    "taf_tracon": ("locid", "scenario", "fiscal_year"),
}


class TerminalAreaForecast(Source):
    id = "faa_taf"
    title = "FAA Terminal Area Forecast (full release)"
    publisher = "Federal Aviation Administration (APO)"
    license = "U.S. Government work — public domain"
    homepage = FAA + "/data_research/aviation/taf"
    history_mode = "latest"  # a new TAF release replaces the previous one (both contain e.g. FY2024)
    period_kind = "version"   # TAF release year, e.g. "2025" (issued March 2026)
    cadence = "annual"
    expected_lag_days = 450
    notes = ("Years are U.S. FISCAL years (Oct-Sep) -> column fiscal_year. Unconstrained by facility capacity, but "
             "the historical baseline reflects past constraints. `scenario` codes are FAA's; see docs.")
    tables = tuple(
        TableSpec(name=t, description=d, required_columns=TAF_REQUIRED[t], not_null=("locid",),
                  unique_key=("locid",) if t == "taf_airport" else ("locid", "scenario", "fiscal_year"),
                  unique_key_blocking=False, min_rows=1000,
                  placeholder_types=tuple((c, "BIGINT") for c in TAF_REQUIRED[t] if c not in ("locid", "region", "state")))
        for t, d in TAF_FILES.values())

    def available_periods(self, http) -> list[str]:
        return sorted(set(re.findall(r"APO100_TAF_Final_(\d{4})\.zip", http.get(self.homepage).text)))

    def fetch(self, period, http) -> FetchResult:
        url = f"https://taf.faa.gov/Downloads/APO100_TAF_Final_{period}.zip"
        r = http.get(url)
        return FetchResult([RawFile(f"APO100_TAF_Final_{period}.zip", r.body)], url, {"method": "GET"},
                           {k: r.headers[k] for k in ("content-type", "content-length", "last-modified", "etag") if k in r.headers})

    def load(self, con, v, staging, tmp):
        tmp.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(v.file(v.files[0]["name"])) as z:
            members = {Path(n).name: n for n in z.namelist()}
            for book, (table, _) in TAF_FILES.items():
                if book not in members:
                    continue  # required-column check will fail the table
                p = tmp / f"taf_{v.vintage_id}_{book}"
                p.write_bytes(z.read(members[book]))
                header, rows = _xlsx_rows(p, "locid")
                cols = ["fiscal_year" if snake(h) == "ayear" else snake(h) for h in header]
                rows_to_table(con, staging[table], cols, rows, tmp, types={"locid": "VARCHAR"})
                p.unlink()
        for table in staging.values():
            exists = scalar(con, "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table])
            if not exists:
                con.execute(f'CREATE TABLE "{table}" (locid VARCHAR)')  # empty -> fails min_rows

    def checks(self, con, v, staging):
        t = staging["taf_enplanements"]
        if "fiscal_year" in {c for (c, *_r) in con.execute(f'DESCRIBE "{t}"').fetchall()}:
            hi = scalar(con, f'SELECT max(fiscal_year) FROM "{t}"')
            yield warning("forecast_horizon", hi is not None and hi >= int(v.period) + 20,
                          f"max fiscal_year {hi}", value=hi)
        # `scenario` semantics are inferred (0 = historical, 1 = forecast); enforce the inference
        for t in ("taf_enplanements", "taf_operations"):
            tt = staging[t]
            r = con.execute(f'''SELECT max(fiscal_year) FILTER (WHERE scenario = 0),
                                       min(fiscal_year) FILTER (WHERE scenario = 1),
                                       count(*) FILTER (WHERE scenario NOT IN (0, 1)) FROM "{tt}"''').fetchone()
            yield error(f"scenario_split:{t}", r[0] is not None and r[1] is not None and r[0] < r[1] and r[2] == 0,
                        f"historical max FY={r[0]}, forecast min FY={r[1]}, other codes={r[2]}", value=list(r))
