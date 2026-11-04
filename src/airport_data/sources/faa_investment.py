"""FAA infrastructure-investment sources: AIP/FAA grant detail reports and NPIAS.

Status semantics are part of the data contract:
  * faa_grants rows are AWARDED grants (federal obligation at award date). They are not project
    completion records; there is no lifecycle status in the source.
  * npias rows are PLANNING ESTIMATES of 5-year AIP-eligible development need from sponsor capital
    plans. They are not funding, approval, or commitment.
"""
from __future__ import annotations

import re

import openpyxl

from ..rawstore import RawFile
from ..validation import error, scalar, warning
from .base import FetchResult, Source, TableSpec, rows_to_table, snake

FAA = "https://www.faa.gov"
GRANT_PAGE = FAA + "/airports/aip/grant_histories"

# funding-program columns of the FY2021+ "FAA Grant Detail Report" layout (snake_case, canonical)
GRANT_ALIASES = {"sum_disc_noise_amt": "discretionary_noise", "sum_disc_map_amt": "discretionary_map",
                 "supp_discretionary_amount": "supp_discretionary", "cares_amount": "cares",
                 "award_date": "award_date", "loc_id": "locid"}
FUNDING_PROGRAMS = ("entitlement", "discretionary", "discretionary_noise", "discretionary_map", "supp_discretionary",
                    "cares", "econ_recover", "aig", "fct", "atrm")


def _sheet_rows(path, hint: str):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    for r in rows:
        if r and any(isinstance(c, str) and c.strip().lower() == hint.lower() for c in r):
            header = [re.sub(r"\s+", " ", str(c)).strip() if c is not None else "" for c in r]
            break
    else:
        raise ValueError(f"header with {hint!r} not found")
    keep = [i for i, h in enumerate(header) if h]
    return [header[i] for i in keep], (tuple(r[i] if i < len(r) else None for i in keep) for r in rows if r)


class FaaGrants(Source):
    id = "faa_grants"
    title = "FAA grant detail report (AIP, AIG/BIL, COVID relief, FCT, ATRM) by grant"
    publisher = "Federal Aviation Administration (Office of Airports)"
    license = "U.S. Government work — public domain"
    homepage = GRANT_PAGE
    period_kind = "year"           # federal fiscal year (Oct-Sep) of award
    period_basis = "fiscal"
    cadence = "annual"
    expected_lag_days = 60
    notes = ("One row per AWARDED grant. Amount columns are funding programs and are additive; "
             "`total_amount` must equal their sum. Fiscal years are federal FY. FY2021+ layout only "
             "(FY<=2020 files use a different per-project layout — not ingested). Program meanings: "
             "entitlement/discretionary = AIP; aig = Airport Infrastructure Grants (BIL); `cares` = the published COVID-relief "
             "column (in FY2021-22 it also carries CRRSA/ARPA dollars — label is the publisher's); econ_recover/"
             "supp_discretionary = supplemental; fct = Federal Contract Tower; atrm = UNVERIFIED label.")
    tables = (TableSpec(
        name="faa_grant",
        description="Awarded FAA airport grant: locid, sponsor, grant number, award date, amount by program, summary.",
        required_columns=("fiscal_year", "state", "city", "worksite", "locid", "sponsor", "grant_number", "award_date",
                          "entitlement", "discretionary", "total_amount", "project_summary"),
        not_null=("fiscal_year", "locid", "grant_number", "total_amount"),
        unique_key=("grant_number",), unique_key_blocking=True,
        min_rows=1000, max_rows=10_000,      # negatives (deobligations) allowed -> warning below
        placeholder_types=(("fiscal_year", "INTEGER"), ("award_date", "DATE"), ("total_amount", "DOUBLE"),
                           ("entitlement", "DOUBLE"), ("discretionary", "DOUBLE")),
    ),)

    def _links(self, http) -> dict[str, str]:
        out = {}
        index = http.get(GRANT_PAGE).text
        years = sorted({int(y) for y in re.findall(r'href="/airports/aip/grant_histories/(20\d\d)"', index)})
        for y in years:
            if y < 2021:
                continue
            page = http.get(f"{GRANT_PAGE}/{y}").text
            hrefs = re.findall(r'href="([^"]+\.xlsx)"', page)
            if hrefs:
                out[str(y)] = hrefs[0] if hrefs[0].startswith("http") else FAA + hrefs[0]
        return out

    def available_periods(self, http) -> list[str]:
        return sorted(self._links(http))

    def fetch(self, period, http) -> FetchResult:
        url = self._links(http)[period]
        r = http.get(url)
        return FetchResult([RawFile(url.rsplit("/", 1)[-1], r.body)], url, {"method": "GET"},
                           {k: r.headers[k] for k in ("content-type", "content-length", "last-modified") if k in r.headers})

    def load(self, con, v, staging, tmp):
        header, rows = _sheet_rows(v.file(v.files[0]["name"]), "LocID")
        cols = [GRANT_ALIASES.get(snake(h), snake(h)) for h in header]
        if len(set(cols)) != len(cols):
            raise ValueError(f"duplicate normalized columns: {cols}")
        # keep data rows only: a real grant number (drops blank and =SUM() footer rows)
        gi = cols.index("grant_number")
        data = (r for r in rows if isinstance(r[gi], str) and re.match(r"\d-\d\d-\d{4}-\d{3}-\d{4}", r[gi].strip()))
        t = staging["faa_grant"]
        rows_to_table(con, t, cols, data, tmp,
                      types={"locid": "VARCHAR", "grant_number": "VARCHAR", "award_date": "TIMESTAMP",
                             **{c: "DOUBLE" for c in FUNDING_PROGRAMS + ("total_amount",)}})
        con.execute(f'''CREATE OR REPLACE TABLE "{t}" AS SELECT {int(v.period)} AS fiscal_year,
                        * REPLACE (CAST(award_date AS DATE) AS award_date) FROM "{t}"''')
        present = {r[0] for r in con.execute(f'DESCRIBE "{t}"').fetchall()}
        for c in FUNDING_PROGRAMS:      # absent program column = 0 for that year's layout? NO: keep NULL
            if c not in present:
                con.execute(f'ALTER TABLE "{t}" ADD COLUMN "{c}" DOUBLE')   # NULL = not reported in this layout

    def checks(self, con, v, staging):
        t = staging["faa_grant"]
        comp = " + ".join(f'coalesce("{c}", 0)' for c in FUNDING_PROGRAMS)
        bad = scalar(con, f'SELECT count(*) FROM "{t}" WHERE abs(total_amount - ({comp})) > 1')
        yield error("total_equals_sum_of_programs", bad == 0,
                    f"{bad} grants where total_amount != sum of program columns", value=bad)
        unknown = [r[0] for r in con.execute(f'DESCRIBE "{t}"').fetchall()
                   if r[1] in ("DOUBLE", "BIGINT", "INTEGER") and r[0] not in FUNDING_PROGRAMS + ("total_amount", "fiscal_year")]
        yield error("no_unknown_amount_columns", not unknown,
                    f"unrecognised numeric columns (new funding program?): {unknown}", value=unknown)
        neg = scalar(con, f'SELECT count(*) FROM "{t}" WHERE total_amount < 0')
        yield warning("negative_totals", neg == 0, f"{neg} grants with negative total (deobligation?)", value=neg)
        ann = scalar(con, f'SELECT count(*) FROM "{t}" WHERE award_date IS NULL')
        yield warning("announced_not_awarded", ann == 0,
                      f"{ann} grants without award date = announced, amounts preliminary (status 'announced')", value=ann)
        fy = scalar(con, f"""SELECT count(*) FROM "{t}" WHERE right(grant_number, 4) <> '{v.period}'""")
        yield warning("grant_number_fy_suffix", fy == 0, f"{fy} grants whose number suffix != FY {v.period}", value=fy)
        out = scalar(con, f"""SELECT count(*) FROM "{t}" WHERE award_date IS NOT NULL AND award_date NOT BETWEEN
                              DATE '{int(v.period) - 1}-10-01' AND DATE '{v.period}-09-30'""")
        yield warning("award_date_in_fiscal_year", out == 0, f"{out} award dates outside FY{v.period}", value=out)


class Npias(Source):
    id = "faa_npias"
    title = "FAA NPIAS Appendix A — airports, roles and 5-year development estimates"
    publisher = "Federal Aviation Administration (Office of Airports)"
    license = "U.S. Government work — public domain"
    homepage = FAA + "/airports/planning_capacity/npias/current"
    period_kind = "version"          # NPIAS cycle, e.g. "2025-2029"
    history_mode = "latest"          # each report replaces the previous (biennial)
    cadence = "biennial"
    expected_lag_days = 0
    notes = ("Development estimate = sponsor-reported AIP-ELIGIBLE capital NEED over the 5-year cycle "
             "(planning estimate; not funded, approved, or committed). Hub/role are FY of the report.")
    tables = (
        TableSpec("npias_airport", "One row per NPIAS airport in the current report.",
                  required_columns=("npias_cycle", "state", "city", "airport", "locid", "ownership", "svc_lvl", "hub",
                                    "role", "enplaned", "based_aircraft", "development_estimate"),
                  not_null=("locid", "npias_cycle"), unique_key=("locid",), unique_key_blocking=True,
                  non_negative=("development_estimate", "enplaned", "based_aircraft"),
                  min_rows=3000, max_rows=4000,
                  placeholder_types=(("development_estimate", "DOUBLE"), ("enplaned", "DOUBLE"),
                                     ("based_aircraft", "DOUBLE"))),
        TableSpec("npias_new_airport", "Proposed new/replacement airports in the NPIAS cycle.",
                  required_columns=("npias_cycle", "state", "locid", "development_estimate"), min_rows=1,
                  placeholder_types=(("development_estimate", "DOUBLE"),)),
    )

    def _link(self, http) -> tuple[str, str]:
        page = http.get(self.homepage).text
        m = re.search(r'href="([^"]*NPIAS-(\d{4})-(\d{4})-Appendix-?A\.xlsx)"', page, re.I)
        if not m:
            raise RuntimeError("NPIAS Appendix A xlsx link not found")
        href = m.group(1).strip()
        return f"{m.group(2)}-{m.group(3)}", href if href.startswith("http") else FAA + href.replace(" ", "")

    def available_periods(self, http) -> list[str]:
        return [self._link(http)[0]]

    def fetch(self, period, http) -> FetchResult:
        cyc, url = self._link(http)
        if cyc != period:
            raise RuntimeError(f"current NPIAS cycle is {cyc}, not {period}")
        r = http.get(url)
        return FetchResult([RawFile(url.rsplit("/", 1)[-1], r.body)], url, {"method": "GET"})

    @staticmethod
    def _norm(h: str) -> str:
        h = re.sub(r"\(.*?\)", "", h)                     # drop "(FY25)", "(CY23/FY25)" — basis kept in npias_cycle notes
        s = snake(h)
        if s.startswith("development_estimate") or "development_cost" in s:
            return "development_estimate"
        return {"loc_id": "locid", "owner_ship": "ownership", "airport_category_upon_opening": "category_upon_opening",
                "fy_anticipated_to_open": "fy_anticipated_to_open"}.get(s, s)

    def load(self, con, v, staging, tmp):
        wb = openpyxl.load_workbook(v.file(v.files[0]["name"]), read_only=True, data_only=True)
        for sheet, table, hint in (("All NPIAS Airports", "npias_airport", "LocID"), ("New Airports", "npias_new_airport", "Locid")):
            ws = wb[sheet]
            it = ws.iter_rows(values_only=True)
            header = next(r for r in it if r and hint in [str(c).strip() if c else "" for c in r])
            keep = [i for i, h in enumerate(header) if h]
            cols = [self._norm(str(header[i])) for i in keep]
            li = cols.index("locid")
            data = (tuple(r[i] for i in keep) for r in it if r and r[keep[li]])
            rows_to_table(con, staging[table], cols, data, tmp,
                          types={"locid": "VARCHAR", "development_estimate": "DOUBLE"})
            con.execute(f'ALTER TABLE "{staging[table]}" ADD COLUMN npias_cycle VARCHAR DEFAULT \'{v.period}\'')
            basis = [str(header[i]) for i in keep if str(header[i]).lower().startswith("enplaned")]
            if basis:   # e.g. "Enplaned (CY23/FY25)": the activity year differs from the estimate cycle
                con.execute(f'ALTER TABLE "{staging[table]}" ADD COLUMN enplaned_basis VARCHAR DEFAULT '
                            f"'{re.sub(r'\s+', ' ', basis[0])}'")

    def checks(self, con, v, staging):
        t = staging["npias_airport"]
        hubs = scalar(con, f"SELECT count(*) FROM \"{t}\" WHERE hub IN ('L','M','S','N')")
        yield error("hub_airports_present", hubs >= 350, f"{hubs} airports with a hub class", value=hubs)
        total = scalar(con, f'SELECT sum(development_estimate) FROM "{t}"')
        yield warning("national_total_plausible", 2e10 < (total or 0) < 2e11,
                      f"national 5-yr development estimate = ${total:,.0f}", value=total)
