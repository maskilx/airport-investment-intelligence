"""Semantic layer: facts, measures, metrics — defined once, used by every analysis.

Rules that make results correct by construction:
  * a MEASURE is an additive aggregate over one fact with fixed built-in filters;
  * a METRIC is an expression over measures, always evaluated at the requested grain
    (ratio of sums, never mean of ratios);
  * a metric declares its unit, epistemic class, definition and caveats; changing semantics bumps
    `formula_version` (findings record it).
  * non-additive metrics (quantiles, top-share) are `custom` and restricted to airport grain.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Callable

CATALOG_VERSION = "2.0.0"

# ------------------------------------------------------------------ facts
PAX = "service_type IN ('passenger', 'combi')"


@dataclass(frozen=True)
class Fact:
    id: str
    relation: str              # SQL producing standard columns: airport_id, t (DATE month | INT year), + dims
    time_kind: str             # month | cy | fy | static
    sources: tuple[str, ...]   # source_ids for lineage
    dims: dict[str, str]       # dimension name -> SQL expression over the relation
    area_key: str | None = None  # distinct-area aggregation key (population etc.)
    description: str = ""


AIRPORT_ATTR_DIMS = ("state", "census_division", "census_region", "hub_class", "cbsa")

FACTS: dict[str, Fact] = {f.id: f for f in [
    Fact("t100_dep", "SELECT *, origin_airport_id AS airport_id, period_month AS t FROM v_t100_segment", "month",
         ("bts_t100_segment",),
         {"carrier": "unique_carrier", "dest": "dest", "international": "is_international",
          "service_type": "service_type", "distance_band":
          "CASE WHEN distance < 500 THEN '0-499' WHEN distance < 1000 THEN '500-999' WHEN distance < 2000 THEN '1000-1999' "
          "WHEN distance < 3000 THEN '2000-2999' ELSE '3000+' END"},
         description="T-100 segments departing the airport (all carriers, domestic + international)"),
    Fact("t100_arr", "SELECT *, dest_airport_id AS airport_id, period_month AS t FROM v_t100_segment", "month",
         ("bts_t100_segment",), {"carrier": "unique_carrier", "international": "is_international",
                                 "service_type": "service_type"},
         description="T-100 segments arriving at the airport"),
    Fact("ontime_dep", "SELECT *, origin_airport_id AS airport_id, period_month AS t FROM v_ontime_flight", "month",
         ("bts_ontime",), {"carrier": "reporting_airline", "hour": "crs_dep_hour"},
         description="On-Time departures (domestic, reporting carriers only)"),
    Fact("ontime_arr", "SELECT *, dest_airport_id AS airport_id, period_month AS t FROM v_ontime_flight", "month",
         ("bts_ontime",), {"carrier": "reporting_airline", "hour": "crs_arr_hour"},
         description="On-Time arrivals (domestic, reporting carriers only)"),
    Fact("atads", "SELECT *, period_month AS t FROM v_atads_airport_ops WHERE airport_id IS NOT NULL", "month",
         ("faa_atads_ops",), {}, description="FAA ATADS tower operations (towered airports, tower hours)"),
    Fact("taf_enp", "SELECT *, fiscal_year AS t FROM v_taf_enplanements WHERE airport_id IS NOT NULL", "fy",
         ("faa_taf",), {"record_type": "record_type"}, description="FAA TAF enplanements (fiscal years)"),
    Fact("taf_ops", "SELECT *, fiscal_year AS t FROM v_taf_operations WHERE airport_id IS NOT NULL", "fy",
         ("faa_taf",), {"record_type": "record_type"}, description="FAA TAF operations (fiscal years)"),
    Fact("acais", "SELECT *, cy AS t FROM v_faa_enplanements_annual WHERE airport_id IS NOT NULL", "cy",
         ("faa_enplanements",), {}, description="FAA CY passenger boardings (ACAIS)"),
    Fact("area_cbsa", """SELECT x.airport_id, e.year AS t, e.cbsa_code AS area, e.population, e.personal_income_usd
                          FROM xref_airport_county x JOIN v_cbsa_econ_annual e ON e.cbsa_code = x.cbsa_code""", "cy",
         ("bea_cainc1", "census_cbsa", "faa_nasr_apt"), {}, area_key="area",
         description="BEA population & income of the airport's home CBSA (distinct-area aggregation)"),
    Fact("area_county", """SELECT x.airport_id, e.year AS t, e.county_fips AS area, e.population, e.personal_income_usd
                            FROM xref_airport_county x JOIN v_county_econ_annual e ON e.county_fips = x.county_fips""", "cy",
         ("bea_cainc1", "faa_nasr_apt"), {}, area_key="area",
         description="BEA population & income of the airport's home county"),
    Fact("grants", "SELECT *, fiscal_year AS t FROM v_faa_grant WHERE airport_id IS NOT NULL", "fy",
         ("faa_grants",), {}, description="Awarded FAA grants (FY2021+)"),
    Fact("npias", """SELECT x.airport_id, NULL::INTEGER AS t, n.* FROM npias_airport n
                      JOIN xref_faa_lid x ON x.faa_lid = n.locid""", "static", ("faa_npias",), {},
         description="NPIAS 2025-2029 development NEED estimates (not funding)"),
    Fact("airport_attr", "SELECT d.*, NULL::INTEGER AS t FROM dim_airport d", "static",
         ("ourairports", "bts_t100_segment"), {}, description="Airport attributes (runways from OurAirports)"),
]}


# ------------------------------------------------------------------ measures
@dataclass(frozen=True)
class Measure:
    id: str
    fact: str
    agg: str                  # SQL aggregate expression; may contain {param} placeholders
    params: tuple[str, ...] = ()
    unit: str = ""


M = Measure
MEASURES: dict[str, Measure] = {m.id: m for m in [
    M("passengers", "t100_dep", f"sum(passengers) FILTER (WHERE {PAX})", unit="passengers"),
    M("seats", "t100_dep", f"sum(seats) FILTER (WHERE {PAX})", unit="seats"),
    M("pax_departures", "t100_dep", f"sum(departures_performed) FILTER (WHERE {PAX})", unit="departures"),
    M("all_departures", "t100_dep", "sum(departures_performed)", unit="departures"),
    M("all_arrivals", "t100_arr", "sum(departures_performed)", unit="arrivals"),
    M("freight_lbs", "t100_dep", "sum(freight)", unit="lbs"),
    M("passenger_miles", "t100_dep", f"sum(passengers * distance) FILTER (WHERE {PAX})", unit="passenger-miles"),
    M("seat_miles", "t100_dep", f"sum(seats * distance) FILTER (WHERE {PAX})", unit="seat-miles"),
    M("seats_intl", "t100_dep", f"sum(seats) FILTER (WHERE {PAX} AND is_international)", unit="seats"),
    M("lh_departures", "t100_dep", "sum(departures_performed) FILTER (WHERE distance >= {min_miles} AND {scope_sql})",
      ("min_miles", "scope_sql"), "departures"),
    M("scope_departures", "t100_dep", "sum(departures_performed) FILTER (WHERE {scope_sql})", ("scope_sql",), "departures"),
    M("lh_passengers", "t100_dep", "sum(passengers) FILTER (WHERE distance >= {min_miles} AND {scope_sql})",
      ("min_miles", "scope_sql"), "passengers"),
    M("scope_passengers", "t100_dep", "sum(passengers) FILTER (WHERE {scope_sql})", ("scope_sql",), "passengers"),
    M("lh_freight", "t100_dep", "sum(freight) FILTER (WHERE distance >= {min_miles} AND {scope_sql})",
      ("min_miles", "scope_sql"), "lbs"),
    M("scope_freight", "t100_dep", "sum(freight) FILTER (WHERE {scope_sql})", ("scope_sql",), "lbs"),
    # On-Time (reporting carriers)
    M("ot_scheduled_deps", "ontime_dep", "count(*)", unit="flights"),
    M("ot_operated_deps", "ontime_dep", "count(*) FILTER (WHERE cancelled = 0)", unit="flights"),
    M("ot_cancelled", "ontime_dep", "sum(cancelled)", unit="flights"),
    M("ot_dep_delayed15", "ontime_dep", "sum(dep_del15) FILTER (WHERE cancelled = 0)", unit="flights"),
    M("ot_dep_delay_minutes", "ontime_dep", "sum(dep_delay_minutes) FILTER (WHERE cancelled = 0)", unit="minutes"),
    M("ot_taxi_out_minutes", "ontime_dep", "sum(taxi_out) FILTER (WHERE cancelled = 0 AND taxi_out IS NOT NULL)", unit="minutes"),
    M("ot_taxi_out_n", "ontime_dep", "count(taxi_out) FILTER (WHERE cancelled = 0)", unit="flights"),
    M("ot_operated_arrs", "ontime_arr", "count(*) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="flights"),
    M("ot_arr_delayed15", "ontime_arr", "sum(arr_del15) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="flights"),
    M("ot_nas_delay_min", "ontime_arr", "sum(nas_delay) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="minutes"),
    M("ot_weather_delay_min", "ontime_arr", "sum(weather_delay) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="minutes"),
    M("ot_carrier_delay_min", "ontime_arr", "sum(carrier_delay) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="minutes"),
    M("ot_late_aircraft_delay_min", "ontime_arr", "sum(late_aircraft_delay) FILTER (WHERE cancelled = 0 AND diverted = 0)", unit="minutes"),
    # ATADS
    M("tower_ops", "atads", "sum(total_operations)", unit="operations"),
    M("tower_ops_air_carrier", "atads", "sum(itn_air_carrier)", unit="operations"),
    M("tower_ops_air_taxi", "atads", "sum(itn_air_taxi)", unit="operations"),
    M("tower_ops_ga", "atads", "sum(itn_general_aviation + local_civil)", unit="operations"),
    M("tower_ops_military", "atads", "sum(itn_military + local_military)", unit="operations"),
    # TAF / ACAIS
    M("taf_enplanements", "taf_enp", "sum(total_enplanements)", unit="enplanements"),
    M("taf_domestic_enplanements", "taf_enp", "sum(domestic_enplanements)", unit="enplanements"),
    M("taf_international_enplanements", "taf_enp", "sum(international_enplanements)", unit="enplanements"),
    M("taf_operations", "taf_ops", "sum(total_ops)", unit="operations"),
    M("acais_enplanements", "acais", "sum(enplanements)", unit="enplanements"),
    # area economics (distinct-area)
    M("cbsa_population", "area_cbsa", "sum(population)", unit="persons"),
    M("cbsa_personal_income", "area_cbsa", "sum(personal_income_usd)", unit="USD"),
    M("county_population", "area_county", "sum(population)", unit="persons"),
    M("county_personal_income", "area_county", "sum(personal_income_usd)", unit="USD"),
    # investment
    M("grants_awarded_usd", "grants", "sum(total_amount) FILTER (WHERE award_date IS NOT NULL)", unit="USD"),
    M("grants_count", "grants", "count(*) FILTER (WHERE award_date IS NOT NULL)", unit="grants"),
    M("npias_need_usd", "npias", "sum(development_estimate)", unit="USD"),
    M("runways_open", "airport_attr", "sum(runways_open)", unit="runways"),
]}


# ------------------------------------------------------------------ metrics
@dataclass(frozen=True)
class Param:
    name: str
    kind: str                       # int | enum
    default: Any
    choices: tuple = ()
    lo: float | None = None
    hi: float | None = None


@dataclass(frozen=True)
class Metric:
    id: str
    name: str
    expr: str                       # expression over measure ids (+ - * / and parentheses), or "custom"
    unit: str
    epistemic_class: str            # observed | calculated | forecast | estimated
    definition: str
    formula_version: str = "1"
    params: tuple[Param, ...] = ()
    caveats: tuple[str, ...] = ()
    custom: Callable | None = None  # for non-additive metrics: fn(engine, ids, window_months, params) -> {airport_id: value}
    custom_fact: str | None = None
    fmt: str = "number"             # number | pct | usd | minutes | ratio


SCOPES = {"passenger": PAX, "freight": "service_type = 'freight'", "all": "TRUE"}

CAVEATS = {
    "ONTIME_SCOPE": "On-Time covers domestic flights of reporting carriers only (no international, no small carriers).",
    "SEGMENT_PAX": "T-100 passengers are segment enplanements (connecting passengers count at each enplanement).",
    "TAF_FORECAST": "FAA TAF values for forecast years are FAA's unconstrained forecast, not observations.",
    "FISCAL_YEAR": "Federal fiscal year (Oct–Sep).",
    "CBSA_PROXY": "Home CBSA is an administrative proxy for the market area, not a measured catchment.",
    "NPIAS_NEED": "NPIAS figures are sponsor-reported 5-year AIP-eligible NEED estimates, not funding.",
    "GRANTS_AWARDED": "Awarded grant dollars at award date; not spending or project completion.",
    "TOWER_SCOPE": "ATADS counts operations at towered airports during tower hours, all user classes.",
    "SEAT_FACTOR_WEAK": "Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.",
    "PEAK_LOWER_BOUND": "Scheduled peak from On-Time is a lower bound on total scheduled operations (reporting carriers only).",
    "OPERATING_CARRIER": "T-100 carriers are operating carriers; regional affiliates appear separately from their mainline partner.",
}


def _peak_hour(q: str):
    def fn(engine, ids, months, params):
        sql = f"""WITH h AS (
            SELECT airport_id, flight_date, hr, count(*) AS n FROM (
                SELECT origin_airport_id AS airport_id, flight_date, crs_dep_hour AS hr FROM v_ontime_flight
                WHERE period_month IN ({engine.month_list(months)}) AND cancelled = 0
                UNION ALL
                SELECT dest_airport_id, flight_date, crs_arr_hour FROM v_ontime_flight
                WHERE period_month IN ({engine.month_list(months)}) AND cancelled = 0) x
            WHERE airport_id IN ({engine.id_list(ids)}) GROUP BY ALL)
            SELECT airport_id, {q} FROM h GROUP BY 1"""
        return dict(engine.con.execute(sql).fetchall())
    return fn


def _top_carrier_share(engine, ids, months, params):
    sql = f"""WITH c AS (SELECT origin_airport_id AS airport_id, unique_carrier, sum(seats) s FROM v_t100_segment
                  WHERE period_month IN ({engine.month_list(months)}) AND {PAX} AND origin_airport_id IN ({engine.id_list(ids)})
                  GROUP BY ALL)
              SELECT airport_id, max(s) / sum(s) FROM c GROUP BY 1 HAVING sum(s) > 0"""
    return dict(engine.con.execute(sql).fetchall())


def _median_taxi(engine, ids, months, params):
    sql = f"""SELECT origin_airport_id, median(taxi_out) FROM v_ontime_flight
              WHERE period_month IN ({engine.month_list(months)}) AND cancelled = 0
                AND origin_airport_id IN ({engine.id_list(ids)}) GROUP BY 1"""
    return dict(engine.con.execute(sql).fetchall())


def _tight_share(engine, ids, months, params):
    thr = float(params["threshold"])
    sql = f"""WITH rm AS (SELECT origin_airport_id AS airport_id, dest, period_month, sum(passengers) p, sum(seats) s
                  FROM v_t100_segment WHERE period_month IN ({engine.month_list(months)}) AND {PAX} AND seats > 0
                    AND origin_airport_id IN ({engine.id_list(ids)}) GROUP BY ALL)
              SELECT airport_id, sum(p) FILTER (WHERE p / s >= {thr}) / sum(p) FROM rm GROUP BY 1"""
    return dict(engine.con.execute(sql).fetchall())


P_MIN_MILES = Param("min_miles", "int", 3000, lo=100, hi=8000)
P_SCOPE = Param("scope", "enum", "passenger", ("passenger", "freight", "all"))
P_WEIGHT = Param("weight", "enum", "passengers", ("departures", "passengers", "freight"))

MT = Metric
METRICS: dict[str, Metric] = {m.id: m for m in [
    MT("passengers", "Enplaned passengers", "passengers", "passengers", "observed",
       "Σ passengers on departing passenger/combi segments", caveats=("SEGMENT_PAX",)),
    MT("seats", "Seats offered", "seats", "seats", "observed", "Σ seats on departing passenger/combi segments"),
    MT("departures", "Passenger departures", "pax_departures", "departures", "observed",
       "Σ departures performed, passenger/combi aircraft"),
    MT("all_departures", "All departures (incl. cargo)", "all_departures", "departures", "observed",
       "Σ departures performed, all aircraft configurations"),
    MT("airline_operations", "Airline operations (T-100)", "all_departures + all_arrivals", "operations", "calculated",
       "Σ T-100 departures + arrivals, all carriers and configurations"),
    MT("freight_lbs", "Freight enplaned", "freight_lbs", "lbs", "observed", "Σ freight on departing segments"),
    MT("seat_factor", "Seat factor", "passengers / seats", "ratio", "calculated",
       "Σ passengers / Σ seats, departing passenger/combi segments", caveats=("SEAT_FACTOR_WEAK",), fmt="pct"),
    MT("segment_load_factor", "Distance-weighted load factor", "passenger_miles / seat_miles", "ratio", "calculated",
       "Σ(passengers·distance) / Σ(seats·distance), departing segments (not system RPM/ASM)", fmt="pct"),
    MT("seats_per_departure", "Average seats per departure (gauge)", "seats / pax_departures", "seats", "calculated",
       "Σ seats / Σ passenger departures"),
    MT("avg_stage_length", "Seat-weighted average stage length", "seat_miles / seats", "miles", "calculated",
       "Σ(seats·distance) / Σ seats"),
    MT("intl_seat_share", "International seat share", "seats_intl / seats", "ratio", "calculated",
       "Σ seats on international segments / Σ seats", fmt="pct"),
    MT("long_haul_share", "Long-haul share", "LONG_HAUL", "ratio", "calculated",
       "share of departing {weight} on segments ≥ {min_miles} statute miles, scope = {scope}",
       params=(P_MIN_MILES, P_SCOPE, P_WEIGHT), fmt="pct"),
    MT("dep_delay15_rate", "Departure delay rate (≥15 min)", "ot_dep_delayed15 / ot_operated_deps", "ratio", "calculated",
       "departures ≥15 min late / operated departures", caveats=("ONTIME_SCOPE",), fmt="pct"),
    MT("arr_delay15_rate", "Arrival delay rate (≥15 min)", "ot_arr_delayed15 / ot_operated_arrs", "ratio", "calculated",
       "arrivals ≥15 min late / operated arrivals", caveats=("ONTIME_SCOPE",), fmt="pct"),
    MT("cancel_rate", "Cancellation rate", "ot_cancelled / ot_scheduled_deps", "ratio", "calculated",
       "cancelled / scheduled departures", caveats=("ONTIME_SCOPE",), fmt="pct"),
    MT("avg_dep_delay_min", "Average departure delay", "ot_dep_delay_minutes / ot_operated_deps", "minutes", "calculated",
       "Σ departure delay minutes (early = 0) / operated departures", caveats=("ONTIME_SCOPE",), fmt="minutes"),
    MT("avg_taxi_out_min", "Average taxi-out", "ot_taxi_out_minutes / ot_taxi_out_n", "minutes", "calculated",
       "Σ taxi-out minutes / flights with taxi-out", caveats=("ONTIME_SCOPE",), fmt="minutes"),
    MT("median_taxi_out_min", "Median taxi-out", "custom", "minutes", "calculated", "median taxi-out, operated departures",
       caveats=("ONTIME_SCOPE",), custom=_median_taxi, custom_fact="ontime_dep", fmt="minutes"),
    MT("nas_delay_min_per_arrival", "NAS delay minutes per arrival", "ot_nas_delay_min / ot_operated_arrs", "minutes",
       "calculated", "Σ NAS (airspace/system) delay minutes / operated arrivals", caveats=("ONTIME_SCOPE",), fmt="minutes"),
    MT("weather_delay_min_per_arrival", "Weather delay minutes per arrival", "ot_weather_delay_min / ot_operated_arrs",
       "minutes", "calculated", "Σ weather delay minutes / operated arrivals", caveats=("ONTIME_SCOPE",), fmt="minutes"),
    MT("ontime_coverage", "On-Time coverage of airline departures", "ot_operated_deps / pax_departures", "ratio",
       "calculated", "operated reporting-carrier departures (On-Time) / passenger departures (T-100), same window",
       caveats=("ONTIME_SCOPE",), fmt="pct"),
    MT("peak_hour_ops_p95", "Scheduled peak hour (95th percentile)", "custom", "operations/hour", "observed",
       "95th percentile over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights",
       caveats=("PEAK_LOWER_BOUND", "ONTIME_SCOPE"), custom=_peak_hour("quantile_cont(n, 0.95)"), custom_fact="ontime_dep"),
    MT("peak_hour_ops_max", "Busiest scheduled hour", "custom", "operations/hour", "observed",
       "maximum over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights",
       caveats=("PEAK_LOWER_BOUND", "ONTIME_SCOPE"), custom=_peak_hour("max(n)"), custom_fact="ontime_dep"),
    MT("top_carrier_share", "Largest operating carrier's seat share", "custom", "ratio", "calculated",
       "max over operating carriers of seat share, departing passenger/combi segments",
       caveats=("OPERATING_CARRIER",), custom=_top_carrier_share, custom_fact="t100_dep", fmt="pct"),
    MT("tight_capacity_pax_share", "Passengers on capacity-tight route-months", "custom", "ratio", "calculated",
       "share of departing passengers on route-months with passengers/seats ≥ {threshold}",
       params=(Param("threshold", "enum", 0.85, (0.85, 0.90, 0.95)),),
       caveats=("SEAT_FACTOR_WEAK",), custom=_tight_share, custom_fact="t100_dep", fmt="pct"),
    MT("tower_operations", "Tower operations (all users)", "tower_ops", "operations", "observed",
       "Σ ATADS operations (takeoffs + landings)", caveats=("TOWER_SCOPE",)),
    MT("ga_ops_share", "General-aviation share of tower operations", "tower_ops_ga / tower_ops", "ratio", "calculated",
       "(itinerant GA + local civil) / total tower operations", caveats=("TOWER_SCOPE",), fmt="pct"),
    MT("military_ops_share", "Military share of tower operations", "tower_ops_military / tower_ops", "ratio",
       "calculated", "military operations / total tower operations", caveats=("TOWER_SCOPE",), fmt="pct"),
    MT("taf_enplanements", "FAA TAF enplanements", "taf_enplanements", "enplanements", "forecast",
       "FAA Terminal Area Forecast total enplanements (domestic + international)", caveats=("TAF_FORECAST", "FISCAL_YEAR")),
    MT("taf_operations", "FAA TAF operations", "taf_operations", "operations", "forecast",
       "FAA Terminal Area Forecast total operations", caveats=("TAF_FORECAST", "FISCAL_YEAR")),
    MT("acais_enplanements", "FAA CY enplanements (ACAIS)", "acais_enplanements", "enplanements", "observed",
       "FAA official calendar-year revenue passenger boardings"),
    MT("cbsa_population", "Home-CBSA population", "cbsa_population", "persons", "observed",
       "BEA population of the airport's home CBSA (distinct areas summed for groups)", caveats=("CBSA_PROXY",)),
    MT("cbsa_per_capita_income", "Home-CBSA per-capita income", "cbsa_personal_income / cbsa_population", "USD",
       "calculated", "BEA personal income / population of the home CBSA", caveats=("CBSA_PROXY",), fmt="usd"),
    MT("county_population", "Home-county population", "county_population", "persons", "observed",
       "BEA population of the airport's home county"),
    MT("grants_awarded_usd", "FAA grants awarded", "grants_awarded_usd", "USD", "observed",
       "Σ awarded FAA grant totals (award date present)", caveats=("GRANTS_AWARDED", "FISCAL_YEAR"), fmt="usd"),
    MT("npias_need_usd", "NPIAS 5-year development need", "npias_need_usd", "USD", "estimated",
       "NPIAS 2025-2029 development estimate", caveats=("NPIAS_NEED",), fmt="usd"),
    MT("npias_need_per_enplanement", "NPIAS need per annual enplanement", "npias_need_usd / acais_enplanements", "USD",
       "estimated", "NPIAS 5-yr need / CY enplanements (window applies to enplanements)", caveats=("NPIAS_NEED",), fmt="usd"),
    MT("runways_open", "Open runways", "runways_open", "runways", "observed", "count of open runways (OurAirports)"),
]}


# ------------------------------------------------------------------ safe expressions
_ALLOWED = (ast.Expression, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Name, ast.Load, ast.Constant,
            ast.UnaryOp, ast.USub)


def expr_names(expr: str) -> set[str]:
    tree = ast.parse(expr, mode="eval")
    for n in ast.walk(tree):
        if not isinstance(n, _ALLOWED):
            raise ValueError(f"disallowed syntax in metric expression: {type(n).__name__}")
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def eval_expr(expr: str, values: dict[str, float | None]) -> float | None:
    """Evaluate with NULL propagation; division by zero -> None (undefined, not 0)."""
    tree = ast.parse(expr, mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            v = values.get(n.id)
            return None if v is None else float(v)
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            return None if v is None else -v
        a, b = ev(n.left), ev(n.right)
        if a is None or b is None:
            return None
        if isinstance(n.op, ast.Add):
            return a + b
        if isinstance(n.op, ast.Sub):
            return a - b
        if isinstance(n.op, ast.Mult):
            return a * b
        return None if b == 0 else a / b
    return ev(tree)


def metric_measures(m: Metric, params: dict) -> dict[str, tuple[Measure, dict]]:
    """Measures (with bound params) a metric needs, keyed by the name used in its expression."""
    if m.expr == "custom":
        return {}
    if m.expr == "LONG_HAUL":
        scope_sql = SCOPES[params["scope"]]
        w = params["weight"]
        num, den = {"departures": ("lh_departures", "scope_departures"), "passengers": ("lh_passengers", "scope_passengers"),
                    "freight": ("lh_freight", "scope_freight")}[w]
        bp = {"min_miles": int(params["min_miles"]), "scope_sql": scope_sql}
        return {"num": (MEASURES[num], bp), "den": (MEASURES[den], {"scope_sql": scope_sql})}
    return {n: (MEASURES[n], {}) for n in expr_names(m.expr)}


def metric_expr(m: Metric) -> str:
    return "num / den" if m.expr == "LONG_HAUL" else m.expr


def validate_catalog() -> None:
    for m in METRICS.values():
        if m.expr not in ("custom", "LONG_HAUL"):
            missing = expr_names(m.expr) - set(MEASURES)
            assert not missing, (m.id, missing)
    for ms in MEASURES.values():
        assert ms.fact in FACTS, ms.id


validate_catalog()
