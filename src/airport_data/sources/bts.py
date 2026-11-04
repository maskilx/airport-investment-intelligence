"""Bureau of Transportation Statistics (TranStats) sources."""
from __future__ import annotations

import codecs
import re
from pathlib import Path

from ..rawstore import RawFile, Vintage
from ..validation import error, period_match_check, scalar, warning
from .base import FetchResult, Source, TableSpec, extract_member, load_csv_snake, month_periods

TRANSTATS = "https://www.transtats.bts.gov"
_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def _latest_banner(html: str) -> str | None:
    m = re.search(r"Latest Available Data:\s*([A-Za-z]+)\s+(\d{4})", html)
    return f"{int(m.group(2)):04d}-{_MONTHS[m.group(1)]:02d}" if m else None


_period_match_check = period_match_check  # shared implementation


# ------------------------------------------------------------------ T-100
class BtsFormSource(Source):
    """A TranStats 'Download' form table (ASP.NET postback with VIEWSTATE replay).

    All available fields are requested so the stored original is as complete
    as the publisher allows; the selected field list is recorded in meta.json.
    """
    table_code: str  # TranStats gnoyr_VQ code
    period_kind = "month"
    cadence = "monthly"
    publisher = "U.S. DOT Bureau of Transportation Statistics"
    license = "U.S. Government work — public domain"

    @property
    def form_url(self) -> str:
        return f"{TRANSTATS}/DL_SelectFields.aspx?gnoyr_VQ={self.table_code}&QO_fu146_anzr=Nv4%20Pn44vr45"

    def available_periods(self, http) -> list[str]:
        page = http.get(self.form_url).text
        latest = _latest_banner(page)
        sel = re.search(r'name="cboYear".*?</select>', page, re.S)
        years = sorted(int(y) for y in re.findall(r'value="(\d{4})"', sel.group(0))) if sel else []
        if not latest or not years:
            raise RuntimeError("could not read available periods from TranStats form")
        return month_periods(f"{years[0]}-01", latest)

    def fetch(self, period: str, http) -> FetchResult:
        year, month = period.split("-")
        page = http.get(self.form_url).text
        hidden = dict(re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page))
        fields = re.findall(r'<input[^>]*type="checkbox"[^>]*name="([A-Z][A-Z_0-9]+)"', page)
        if not fields or "__VIEWSTATE" not in hidden:
            raise RuntimeError("TranStats form layout changed: no fields / VIEWSTATE found")
        data = dict(hidden)
        data.update({"cboGeography": "All", "cboYear": year, "cboPeriod": str(int(month)), "btnDownload": "Download"})
        data.update({f: "on" for f in fields})
        r = http.post(self.form_url, data)
        if not r.body.startswith(b"PK"):
            raise RuntimeError(f"expected zip, got {r.headers.get('content-type')}: {r.body[:200]!r}")
        return FetchResult(
            files=[RawFile(f"{self.id}_{year}_{month}.zip", r.body)],
            url=self.form_url,
            request={"method": "POST", "table_code": self.table_code, "cboGeography": "All",
                     "cboYear": year, "cboPeriod": str(int(month)), "fields": fields},
            response_headers={k: r.headers[k] for k in ("content-type", "content-length", "last-modified", "etag") if k in r.headers},
            source_reported={"latest_available": _latest_banner(page)},
        )


class T100SegmentAllCarriers(BtsFormSource):
    id = "bts_t100_segment"
    title = "T-100 Segment (All Carriers): monthly nonstop segment traffic & capacity"
    homepage = "https://www.transtats.bts.gov/Tables.asp?QO_VQ=EEE"
    table_code = "FMG"
    expected_lag_days = 100
    notes = ("US + foreign carriers, domestic + international segments touching the US. "
             "PASSENGERS = on-board segment passengers (incl. through pax). "
             "Use AIRCRAFT_CONFIG (1 pax, 2 freight, 3 combi) to split pax vs cargo flying. "
             "BTS revises back-months; each re-download with different content is a new vintage.")
    tables = (TableSpec(
        name="t100_segment",
        description="One row per carrier x origin x dest x aircraft type/config x service class x month.",
        required_columns=("year", "month", "unique_carrier", "unique_carrier_entity", "region", "carrier_name", "origin", "dest", "origin_airport_id",
                          "dest_airport_id", "origin_city_name", "dest_city_name", "origin_state_abr",
                          "dest_state_abr", "origin_country", "dest_country", "departures_scheduled",
                          "departures_performed", "seats", "passengers", "freight", "mail", "distance",
                          "aircraft_type", "aircraft_config", "class", "data_source"),
        not_null=("year", "month", "origin", "dest", "unique_carrier", "origin_airport_id", "dest_airport_id"),
        # true grain (audit F9): carrier entity and region distinguish otherwise identical rows
        unique_key=("year", "month", "unique_carrier", "unique_carrier_entity", "region", "origin_airport_id",
                    "dest_airport_id", "aircraft_type", "aircraft_config", "class", "data_source"),
        unique_key_blocking=True,
        non_negative=("departures_performed", "seats", "passengers", "freight", "distance"),
        min_rows=25_000, max_rows=150_000,
        placeholder_types=tuple({**{c: "BIGINT" for c in ("year", "month", "origin_airport_id", "dest_airport_id",
                                                           "aircraft_config")},
                                 **{c: "DOUBLE" for c in ("departures_scheduled", "departures_performed", "seats",
                                                          "passengers", "freight", "mail", "distance")}}.items()),
    ),)

    def load(self, con, v: Vintage, staging, tmp: Path) -> None:
        csv = extract_member(v, v.files[0]["name"], r"\.csv$", tmp)
        load_csv_snake(con, csv, staging["t100_segment"],
                       types={**{c: "DOUBLE" for c in ("departures_scheduled", "departures_performed", "payload", "seats",
                                                       "passengers", "freight", "mail", "distance", "ramp_to_ramp",
                                                       "air_time")},
                              "year": "INTEGER", "month": "INTEGER", "quarter": "INTEGER",
                              "origin_airport_id": "INTEGER", "dest_airport_id": "INTEGER",
                              "aircraft_config": "INTEGER", "aircraft_type": "VARCHAR", "aircraft_group": "INTEGER",
                              "origin_state_fips": "VARCHAR", "dest_state_fips": "VARCHAR",
                              "unique_carrier_entity": "VARCHAR", "airline_id": "INTEGER"})
        csv.unlink()

    def checks(self, con, v, staging):
        t = staging["t100_segment"]
        yield _period_match_check(con, t, v.period)
        loops = scalar(con, f'SELECT count(*) FROM "{t}" WHERE origin = dest')
        yield warning("self_loop_rows", loops == 0, f"{loops} rows with origin = dest (excluded in v_t100_segment)", value=loops)
        over = scalar(con, f'SELECT count(*) FROM "{t}" WHERE seats > 0 AND passengers > seats')
        yield warning("passengers_le_seats", over == 0, f"{over} rows with passengers > seats", value=over)
        z = scalar(con, f'SELECT count(*) FROM "{t}" WHERE seats = 0 AND passengers > 0')
        yield warning("passengers_without_seats", z == 0, f"{z} rows with passengers but 0 seats", value=z)
        cfg = scalar(con, f'SELECT count(*) FROM "{t}" WHERE aircraft_config NOT IN (0,1,2,3,4,9)')
        yield error("aircraft_config_domain", cfg == 0, f"{cfg} rows with unknown aircraft_config", value=cfg)


# ------------------------------------------------------------------ On-Time
class OnTimeReporting(Source):
    id = "bts_ontime"
    title = "Reporting Carrier On-Time Performance (flight-level)"
    publisher = "U.S. DOT Bureau of Transportation Statistics"
    license = "U.S. Government work — public domain"
    homepage = "https://www.transtats.bts.gov/Tables.asp?QO_VQ=EFD"
    period_kind = "month"
    cadence = "monthly"
    expected_lag_days = 75
    notes = ("Only carriers with >=0.5% of domestic scheduled passenger revenue; mandatory only at airports with "
             ">=0.5% of domestic enplanements (lower 48). No international flights. Delay-cause minutes only for "
             "flights >=15 min late.")
    prezip = "https://transtats.bts.gov/PREZIP/"
    tables = (TableSpec(
        name="ontime_flight",
        description="One row per scheduled domestic flight operated by a reporting carrier.",
        required_columns=("year", "month", "flight_date", "reporting_airline", "flight_number_reporting_airline",
                          "origin", "dest", "origin_airport_id", "dest_airport_id", "origin_state", "dest_state",
                          "origin_city_name", "dest_city_name", "crs_dep_time", "dep_time", "dep_delay", "dep_del15", "taxi_out",
                          "taxi_in", "crs_arr_time", "arr_delay", "arr_del15", "cancelled", "cancellation_code",
                          "diverted", "distance", "carrier_delay", "weather_delay", "nas_delay",
                          "security_delay", "late_aircraft_delay", "dep_time_blk", "arr_time_blk"),
        not_null=("year", "month", "flight_date", "origin", "dest", "origin_airport_id", "dest_airport_id",
                  "reporting_airline", "cancelled"),
        # wide sanity band (Apr-2020 ~150k, peaks ~650k); corrupt downloads are caught by the zip CRC first
        min_rows=100_000, max_rows=1_000_000,
        placeholder_types=tuple({**{c: "BIGINT" for c in ("year", "month", "origin_airport_id", "dest_airport_id")},
                                 **{c: "DOUBLE" for c in ("dep_delay", "dep_del15", "taxi_out", "taxi_in", "arr_delay",
                                    "arr_del15", "cancelled", "diverted", "distance", "carrier_delay", "weather_delay",
                                    "nas_delay", "security_delay", "late_aircraft_delay")},
                                 "flight_date": "DATE"}.items()),
    ),)

    def _name(self, period: str) -> str:
        y, m = period.split("-")
        return f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{int(y)}_{int(m)}.zip"

    def available_periods(self, http) -> list[str]:
        names = re.findall(r"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_(\d{4})_(\d{1,2})\.zip",
                           http.get(self.prezip).text)
        return sorted({f"{int(y):04d}-{int(m):02d}" for y, m in names})

    def fetch(self, period: str, http) -> FetchResult:
        url = self.prezip + self._name(period)
        r = http.get(url)
        return FetchResult([RawFile(self._name(period), r.body)], url, {"method": "GET"},
                           {k: r.headers[k] for k in ("content-type", "content-length", "last-modified", "etag") if k in r.headers})

    def load(self, con, v, staging, tmp):
        csv = extract_member(v, v.files[0]["name"], r"\.csv$", tmp)
        load_csv_snake(con, csv, staging["ontime_flight"], types={
            "flight_date": "DATE", "year": "INTEGER", "month": "INTEGER", "origin_airport_id": "INTEGER",
            "dest_airport_id": "INTEGER", "cancelled": "DOUBLE", "diverted": "DOUBLE", "dep_del15": "DOUBLE",
            "arr_del15": "DOUBLE", "distance": "DOUBLE", "crs_dep_time": "VARCHAR", "dep_time": "VARCHAR", "crs_arr_time": "VARCHAR",
            "arr_time": "VARCHAR", "wheels_off": "VARCHAR", "wheels_on": "VARCHAR", "first_dep_time": "VARCHAR",
            "cancellation_code": "VARCHAR", "tail_number": "VARCHAR", "flight_number_reporting_airline": "VARCHAR",
            "dep_delay": "DOUBLE", "arr_delay": "DOUBLE", "taxi_out": "DOUBLE", "taxi_in": "DOUBLE",
            "carrier_delay": "DOUBLE", "weather_delay": "DOUBLE", "nas_delay": "DOUBLE",
            "security_delay": "DOUBLE", "late_aircraft_delay": "DOUBLE",
            **{f"div{i}_{c}": "VARCHAR" for i in range(1, 6) for c in
               ("airport", "tail_num", "wheels_on", "wheels_off")},
        })
        # drop the trailing unnamed column BTS files end with (null_padding)
        cols = [c for (c, *_rest) in con.execute(f'DESCRIBE "{staging["ontime_flight"]}"').fetchall()]
        for c in cols:
            if re.fullmatch(r"column\d+", c):
                con.execute(f'ALTER TABLE "{staging["ontime_flight"]}" DROP COLUMN "{c}"')
        csv.unlink()

    def checks(self, con, v, staging):
        t = staging["ontime_flight"]
        yield _period_match_check(con, t, v.period)
        bad = scalar(con, f'SELECT count(*) FROM "{t}" WHERE cancelled NOT IN (0, 1)')
        yield error("cancelled_is_flag", bad == 0, f"{bad} rows with cancelled not in (0,1)", value=bad)


# ------------------------------------------------------------------ lookups
class BtsLookups(Source):
    """BTS code lists (snapshot), discovered from the lookup links on the form pages
    of the tables we ingest. TranStats encodes names with mixed-case ROT13, so the
    encoded key is taken verbatim from the page and only decoded for naming."""
    id = "bts_lookups"
    title = "TranStats lookup tables (codes -> descriptions)"
    publisher = "U.S. DOT Bureau of Transportation Statistics"
    license = "U.S. Government work — public domain"
    homepage = TRANSTATS
    period_kind = "snapshot"
    history_mode = "latest"
    cadence = "manual"
    expected_lag_days = 0
    FORM_PAGES = (f"{TRANSTATS}/DL_SelectFields.aspx?gnoyr_VQ=FMG&QO_fu146_anzr=Nv4%20Pn44vr45",   # T-100
                  f"{TRANSTATS}/DL_SelectFields.aspx?gnoyr_VQ=FGJ&QO_fu146_anzr=b0-gvzr")           # On-Time
    tables = (TableSpec(
        name="bts_lookup",
        description="Long-format code list: lookup name, code, description.",
        required_columns=("lookup", "code", "description"),
        not_null=("lookup", "code"),
        unique_key=("lookup", "code"), unique_key_blocking=False,  # L_CARRIER_HISTORY reuses codes over time
        min_rows=1000,
    ),)
    JOIN_LOOKUPS = ("L_AIRCRAFT_CONFIG", "L_SERVICE_CLASS", "L_AIRPORT", "L_AIRPORT_ID", "L_AIRCRAFT_TYPE")

    def checks(self, con, v, staging):
        t = staging["bts_lookup"]
        for lk in self.JOIN_LOOKUPS:
            n, d = con.execute(f'SELECT count(*), count(*) - count(DISTINCT code) FROM "{t}" WHERE lookup = ?', [lk]).fetchone()
            yield error(f"lookup_present_unique:{lk}", n > 0 and d == 0, f"{n} codes, {d} duplicates", value=n)

    def available_periods(self, http) -> list[str]:
        from .base import today
        return [today().isoformat()]

    def fetch(self, period, http) -> FetchResult:
        keys: dict[str, str] = {}
        for page in self.FORM_PAGES:
            for key in re.findall(r"Download_Lookup\.asp\?Y11x72=([A-Za-z_]+)", http.get(page).text):
                keys[codecs.decode(key, "rot13").upper()] = key
        if len(keys) < 5:
            raise RuntimeError(f"only {len(keys)} lookup links found — form layout changed?")
        files = []
        for name, key in sorted(keys.items()):
            r = http.get(f"{TRANSTATS}/Download_Lookup.asp?Y11x72={key}")
            if not r.text.startswith("Code,Description"):
                raise RuntimeError(f"{name}: unexpected lookup format")
            files.append(RawFile(f"{name}.csv", r.body))
        return FetchResult(files, f"{TRANSTATS}/Download_Lookup.asp", {"method": "GET", "lookups": keys,
                                                                       "discovered_from": list(self.FORM_PAGES)})

    def load(self, con, v, staging, tmp):
        parts = [f"SELECT '{f['name'][:-4]}' AS lookup, CAST(\"Code\" AS VARCHAR) AS code, \"Description\" AS description "
                 f"FROM read_csv('{v.file(f['name'])}', header=true, all_varchar=true, encoding='latin-1')"
                 for f in v.files]   # TranStats lookups are Latin-1, not UTF-8
        con.execute(f'CREATE OR REPLACE TABLE "{staging["bts_lookup"]}" AS ' + " UNION ALL ".join(parts))
