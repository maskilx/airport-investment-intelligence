"""Geography & regional economy: FAA NASR airport records, Census CBSA delineation, BEA county income.

Purpose: attach each airport to an official county (NASR) and metro area (CBSA), and give those
areas population / personal income time series (BEA CAINC1, derived from Census population).
"""
from __future__ import annotations

import re
import zipfile

import openpyxl

from ..rawstore import RawFile
from ..validation import error, scalar, warning
from .base import FetchResult, Source, TableSpec, extract_member, load_csv_snake, rows_to_table, snake, today

NASR_INDEX = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"


class NasrAirports(Source):
    id = "faa_nasr_apt"
    title = "FAA NASR airport & runway records (28-day cycle, CSV extract)"
    publisher = "Federal Aviation Administration (NFDC)"
    license = "U.S. Government work — public domain"
    homepage = NASR_INDEX
    period_kind = "snapshot"        # NASR cycle effective date YYYY-MM-DD
    history_mode = "latest"
    cadence = "28-day"
    expected_lag_days = 0
    notes = "Official FAA airport master record (5010): county, ownership, use, coordinates; APT_RWY runways."
    tables = (
        TableSpec("nasr_airport", "APT_BASE: one row per landing facility (all US public/private).",
                  required_columns=("eff_date", "site_no", "site_type_code", "state_code", "arpt_id", "city",
                                    "county_name", "county_assoc_state", "arpt_name", "ownership_type_code",
                                    "facility_use_code", "lat_decimal", "long_decimal", "arpt_status"),
                  not_null=("arpt_id", "site_no"), unique_key=("arpt_id",), unique_key_blocking=True, min_rows=15_000),
        TableSpec("nasr_runway", "APT_RWY: one row per runway.",
                  required_columns=("site_no", "arpt_id", "rwy_id", "rwy_len", "rwy_width"),
                  not_null=("site_no", "rwy_id"), min_rows=15_000),
    )

    def _cycles(self, http) -> list[str]:
        page = http.get(NASR_INDEX).text
        return sorted(set(re.findall(r"NASR_Subscription/(\d{4}-\d{2}-\d{2})", page)))

    def available_periods(self, http) -> list[str]:
        t = today().isoformat()
        return [c for c in self._cycles(http) if c <= t][-1:]      # current effective cycle

    def fetch(self, period, http) -> FetchResult:
        page = http.get(NASR_INDEX + period).text
        m = re.search(r'href="([^"]+_APT_CSV\.zip)"', page)
        if not m:
            raise RuntimeError(f"APT CSV link not found for cycle {period}")
        r = http.get(m.group(1))
        return FetchResult([RawFile(m.group(1).rsplit("/", 1)[-1], r.body)], m.group(1), {"method": "GET", "cycle": period})

    def load(self, con, v, staging, tmp):
        z = v.files[0]["name"]
        for member, table in ((r"(^|/)APT_BASE\.csv$", "nasr_airport"), (r"(^|/)APT_RWY\.csv$", "nasr_runway")):
            p = extract_member(v, z, member, tmp)
            load_csv_snake(con, p, staging[table], all_varchar=True)
            p.unlink()
        con.execute(f'''CREATE OR REPLACE TABLE "{staging["nasr_airport"]}" AS SELECT * REPLACE (
                        TRY_CAST(lat_decimal AS DOUBLE) AS lat_decimal, TRY_CAST(long_decimal AS DOUBLE) AS long_decimal)
                        FROM "{staging["nasr_airport"]}"''')
        con.execute(f'''CREATE OR REPLACE TABLE "{staging["nasr_runway"]}" AS SELECT * REPLACE (
                        TRY_CAST(rwy_len AS INTEGER) AS rwy_len, TRY_CAST(rwy_width AS INTEGER) AS rwy_width)
                        FROM "{staging["nasr_runway"]}"''')

    def checks(self, con, v, staging):
        t = staging["nasr_airport"]
        n = scalar(con, f"SELECT count(*) FROM \"{t}\" WHERE coalesce(county_name, '') = '' AND country_code = 'US'")
        yield warning("county_present", n < 50, f"{n} US facilities without county", value=n)
        d = scalar(con, f'SELECT count(*) FROM (SELECT site_no FROM "{t}" GROUP BY 1 HAVING count(*) > 1)')
        yield warning("site_no_unique", d == 0, f"{d} SITE_NO values shared by >1 facility (publisher defect; key is ARPT_ID)", value=d)


class CensusCbsaDelineation(Source):
    id = "census_cbsa"
    title = "Census/OMB CBSA delineation (county -> metro/micro area)"
    publisher = "U.S. Census Bureau (OMB delineations)"
    license = "U.S. Government work — public domain"
    homepage = "https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html"
    period_kind = "version"         # delineation vintage year, e.g. "2023"
    history_mode = "latest"
    cadence = "irregular"
    expected_lag_days = 0
    URL = "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/{y}/delineation-files/list1_{y}.xlsx"
    tables = (TableSpec("cbsa_county", "One row per county in a CBSA (List 1).",
                        required_columns=("cbsa_code", "cbsa_title", "metro_micro", "csa_code", "csa_title",
                                          "county_fips", "county_name", "state_name", "central_outlying"),
                        not_null=("cbsa_code", "county_fips"), unique_key=("county_fips",), unique_key_blocking=True,
                        min_rows=1500),)

    def available_periods(self, http) -> list[str]:
        return ["2023"]     # latest OMB delineation (Bulletin 23-01); bump when OMB issues a new one

    def fetch(self, period, http) -> FetchResult:
        url = self.URL.format(y=period)
        r = http.get(url)
        return FetchResult([RawFile(url.rsplit("/", 1)[-1], r.body)], url, {"method": "GET"})

    def load(self, con, v, staging, tmp):
        ws = openpyxl.load_workbook(v.file(v.files[0]["name"]), read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = next(r for r in it if r and r[0] == "CBSA Code")
        idx = {h: i for i, h in enumerate(header)}

        def rows():
            for r in it:
                if not r or not r[0] or not str(r[0]).strip().isdigit():
                    continue    # footnotes
                g = lambda k: r[idx[k]]
                yield (g("CBSA Code"), g("CBSA Title"), g("Metropolitan/Micropolitan Statistical Area"), g("CSA Code"),
                       g("CSA Title"), f"{int(g('FIPS State Code')):02d}{int(g('FIPS County Code')):03d}",
                       g("County/County Equivalent"), g("State Name"), g("Central/Outlying County"))
        rows_to_table(con, staging["cbsa_county"], list(self.tables[0].required_columns), rows(), tmp,
                      types={c: "VARCHAR" for c in self.tables[0].required_columns})


class BeaCountyIncome(Source):
    id = "bea_cainc1"
    title = "BEA CAINC1: county personal income, population, per-capita income (annual)"
    publisher = "U.S. Bureau of Economic Analysis"
    license = "U.S. Government work — public domain"
    homepage = "https://apps.bea.gov/regional/downloadzip.htm"
    period_kind = "version"         # data span in the release, e.g. "1969-2024"
    history_mode = "latest"         # each release revises the whole history
    cadence = "annual"
    expected_lag_days = 0
    URL = "https://apps.bea.gov/regional/zip/CAINC1.zip"
    notes = ("Population line = Census midyear estimates as used by BEA. Values flagged (D)/(NA)/(NM) are "
             "suppressed -> NULL with value_flag. Some Virginia independent cities are BEA combination areas.")
    tables = (TableSpec("bea_county_income", "Long format: geo x line (1 income, 2 population, 3 per-capita) x year.",
                        required_columns=("geofips", "geoname", "line_code", "description", "unit", "year", "value", "value_flag"),
                        not_null=("geofips", "line_code", "year"), unique_key=("geofips", "line_code", "year"),
                        unique_key_blocking=True, min_rows=100_000,
                        placeholder_types=(("year", "INTEGER"), ("value", "DOUBLE"), ("line_code", "INTEGER"))),)

    def available_periods(self, http) -> list[str]:
        return ["latest-release"]    # resolved to the real span at fetch (inner file name), recorded in meta

    def fetch(self, period, http) -> FetchResult:
        r = http.get(self.URL)
        import io
        with zipfile.ZipFile(io.BytesIO(r.body)) as z:
            m = next((re.search(r"ALL_AREAS_(\d{4})_(\d{4})", n) for n in z.namelist() if "ALL_AREAS" in n), None)
        span = f"{m.group(1)}-{m.group(2)}" if m else "unknown"
        return FetchResult([RawFile("CAINC1.zip", r.body)], self.URL, {"method": "GET"}, source_reported={"data_span": span})

    def load(self, con, v, staging, tmp):
        p = extract_member(v, "CAINC1.zip", r"ALL_AREAS_\d{4}_\d{4}\.csv$", tmp)
        raw = f"{staging['bea_county_income']}_raw"
        con.execute(f"CREATE OR REPLACE TABLE \"{raw}\" AS SELECT * FROM read_csv('{p}', header=true, all_varchar=true, "
                    f"encoding='latin-1', null_padding=true)")
        years = [c for (c, *_r) in con.execute(f'DESCRIBE "{raw}"').fetchall() if re.fullmatch(r"\d{4}", c)]
        con.execute(f'''CREATE OR REPLACE TABLE "{staging['bea_county_income']}" AS
            SELECT trim(replace("GeoFIPS", '"', '')) AS geofips, trim("GeoName") AS geoname,
                   TRY_CAST("LineCode" AS INTEGER) AS line_code, trim("Description") AS description, trim("Unit") AS unit,
                   CAST(year AS INTEGER) AS year, TRY_CAST(trim(val) AS DOUBLE) AS value,
                   CASE WHEN TRY_CAST(trim(val) AS DOUBLE) IS NULL THEN trim(val) END AS value_flag
            FROM (UNPIVOT "{raw}" ON {", ".join(f'"{y}"' for y in years)} INTO NAME year VALUE val)
            WHERE TRY_CAST("LineCode" AS INTEGER) IS NOT NULL''')
        con.execute(f'DROP TABLE "{raw}"')
        p.unlink()

    def checks(self, con, v, staging):
        t = staging["bea_county_income"]
        us = con.execute(f"""SELECT value FROM "{t}" WHERE geofips = '00000' AND line_code = 2
                             ORDER BY year DESC LIMIT 1""").fetchone()
        yield error("us_population_plausible", bool(us) and 3.0e8 < us[0] < 4.0e8, f"latest US population {us}")
        cty = scalar(con, f"""SELECT count(DISTINCT geofips) FROM "{t}" WHERE right(geofips, 3) <> '000'""")
        yield error("county_count_plausible", 3000 <= cty <= 3300, f"{cty} county-level areas", value=cty)
        # additivity: counties of each state sum to the state's population (latest year), within 0.5%
        bad = scalar(con, f"""WITH y AS (SELECT max(year) m FROM "{t}"),
            c AS (SELECT left(geofips, 2) st, sum(value) s FROM "{t}", y WHERE line_code = 2 AND year = y.m
                  AND right(geofips, 3) <> '000' AND left(geofips, 2) NOT IN ('00') GROUP BY 1),
            s AS (SELECT left(geofips, 2) st, value FROM "{t}", y WHERE line_code = 2 AND year = y.m AND right(geofips, 3) = '000')
            SELECT count(*) FROM c JOIN s USING (st) WHERE abs(c.s / s.value - 1) > 0.005""")
        yield warning("counties_sum_to_states", bad == 0, f"{bad} states whose counties don't sum to the state total", value=bad)
