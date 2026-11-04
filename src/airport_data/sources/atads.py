"""FAA ATADS (OPSNET airport operations) — monthly tower-counted operations by user class.

Access: the public ATADS "Standard Report" form (guest mode, no login). The form's JavaScript builds
the request (including a query string in `line`) client-side. We replay *exactly* the payload the
form itself generates (captured from the page's own checkForm(), see atads_payload.json), varying
only the month. No hand-built queries.

Semantics (NOT interchangeable with BTS On-Time):
  * counts are tower-observed operations (one takeoff OR one landing = 1 operation), all users
    (air carrier, air taxi, general aviation, military), itinerant + local;
  * only airports with an FAA or contract tower (~520), only hours the tower is open;
  * BTS On-Time counts scheduled flights of large reporting carriers, per flight leg.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..rawstore import RawFile
from ..validation import error, scalar, warning
from .base import FetchResult, Source, TableSpec, month_periods, rows_to_table

_TEMPLATE = json.loads(Path(__file__).with_name("atads_payload.json").read_text())
COLUMNS = ["period_mmyyyy", "locid", "itn_air_carrier", "itn_air_taxi", "itn_general_aviation", "itn_military",
           "itn_total", "local_civil", "local_military", "local_total", "total_operations"]
NUMERIC = COLUMNS[2:]


def _payload(period: str) -> dict[str, str]:
    y, m = period.split("-")
    sub = {"{YYYYMM}": y + m, "{MM}": m, "{YYYY}": y}
    out = {}
    for k, v in _TEMPLATE["payload"].items():
        for a, b in sub.items():
            v = v.replace(a, b)
        out[k] = v
    return out


def _cells(tr: str) -> list[str]:
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]


def parse_report(text: str) -> tuple[list[list[str]], list[str] | None]:
    """Return (data rows, grand-total row). Sub-total rows are dropped."""
    rows, total = [], None
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        c = _cells(tr)
        if len(c) == 11 and re.fullmatch(r"\d{2}/\d{4}", c[0]) and re.fullmatch(r"[A-Z0-9]{3,4}", c[1]):
            rows.append(c)
        elif c and c[0].startswith("Total:"):
            total = c[-9:]
    return rows, total


class AtadsAirportOperations(Source):
    id = "faa_atads_ops"
    title = "FAA ATADS/OPSNET airport operations by user class (monthly, towered airports)"
    publisher = "Federal Aviation Administration (ATADS via ASPM/OPSNET public pages)"
    license = "U.S. Government work — public domain"
    homepage = _TEMPLATE["form_url"]
    period_kind = "month"
    cadence = "monthly"
    expected_lag_days = 25          # final data public ~20th of the following month
    notes = ("Tower counts of operations (takeoffs + landings) by user class at FAA/contract-towered airports, "
             "tower hours only. Not comparable 1:1 with BTS On-Time flights or T-100 departures.")
    tables = (TableSpec(
        name="atads_airport_ops",
        description="One row per towered airport (FAA LOCID) per month.",
        required_columns=tuple(COLUMNS[1:]) + ("year", "month"),
        not_null=("locid", "year", "month", "total_operations"),
        unique_key=("locid", "year", "month"), unique_key_blocking=True,
        non_negative=tuple(NUMERIC),
        min_rows=400, max_rows=700,
        placeholder_types=(("year", "INTEGER"), ("month", "INTEGER"), *((c, "BIGINT") for c in NUMERIC)),
    ),)

    def available_periods(self, http) -> list[str]:
        # The form offers months from FY1990; publication lag ~20 days. Probe = attempt fetch; here we
        # derive candidates and let `fetch` + validation decide (an unpublished month returns no rows).
        from .base import today
        t = today()
        last = f"{t.year:04d}-{t.month:02d}"
        return month_periods("1990-01", last)[:-1]

    def fetch(self, period: str, http) -> FetchResult:
        http.get(_TEMPLATE["form_url"])           # establishes the session cookie exactly like a browser
        payload = _payload(period)
        r = http.post(_TEMPLATE["post_url"], payload, headers={"Referer": _TEMPLATE["form_url"]})
        if "Standard Report" not in r.text:
            raise RuntimeError(f"unexpected ATADS response ({r.headers.get('content-type')}): {r.text[:200]!r}")
        rows, total = parse_report(r.text)
        if not rows:
            raise RuntimeError(f"ATADS returned no rows for {period} (not yet published?)")
        return FetchResult([RawFile(f"atads_airport_ops_{period}.xls.html", r.body)], _TEMPLATE["post_url"],
                           {"method": "POST", "payload_template": "atads_payload.json", "period": period},
                           {k: r.headers[k] for k in ("content-type", "content-disposition") if k in r.headers})

    def integrity_errors(self, files):
        errs = []
        for f in files:
            text = f.content.decode("utf-8", "replace")
            rows, total = parse_report(text)
            if not rows or total is None:
                errs.append(f"{f.name}: no data rows or no grand-total row (truncated/partial report?)")
        return errs

    def load(self, con, v, staging, tmp):
        text = v.file(v.files[0]["name"]).read_text(errors="replace")
        rows, _ = parse_report(text)
        t = staging["atads_airport_ops"]
        rows_to_table(con, t, COLUMNS, ([r[0], r[1], *[x.replace(",", "") or None for x in r[2:]]] for r in rows), tmp,
                      types={"period_mmyyyy": "VARCHAR", "locid": "VARCHAR", **{c: "BIGINT" for c in NUMERIC}})
        con.execute(f'''CREATE OR REPLACE TABLE "{t}" AS SELECT
                          CAST(split_part(period_mmyyyy, '/', 2) AS INTEGER) AS year,
                          CAST(split_part(period_mmyyyy, '/', 1) AS INTEGER) AS month,
                          * EXCLUDE (period_mmyyyy) FROM "{t}"''')

    def checks(self, con, v, staging):
        from ..validation import period_match_check
        t = staging["atads_airport_ops"]
        yield period_match_check(con, t, v.period)
        # the report's own grand total must equal the sum of the rows we parsed (no lost/duplicated rows)
        _, total = parse_report(v.file(v.files[0]["name"]).read_text(errors="replace"))
        try:
            want = [int(x.replace(",", "")) for x in total]
        except (TypeError, ValueError):
            yield error("rows_sum_to_report_total", False, f"unparseable total row {total}")
            return
        got = con.execute(f'SELECT {", ".join(f"sum({c})" for c in NUMERIC)} FROM "{t}"').fetchone()
        yield error("rows_sum_to_report_total", list(got) == want, f"parsed {list(got)} vs report {want}")
        bad = scalar(con, f'SELECT count(*) FROM "{t}" WHERE itn_total IS DISTINCT FROM itn_air_carrier + itn_air_taxi + '
                          f'itn_general_aviation + itn_military OR local_total IS DISTINCT FROM local_civil + local_military '
                          f'OR total_operations IS DISTINCT FROM itn_total + local_total')
        yield error("component_sums", bad == 0, f"{bad} rows whose components do not add up", value=bad)
        zero = scalar(con, f'SELECT count(*) FROM "{t}" WHERE total_operations = 0')
        yield warning("zero_operation_rows", True, f"{zero} towered airports reporting 0 operations", value=zero)
