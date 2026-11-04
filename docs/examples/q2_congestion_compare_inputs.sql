-- Q2 validation case: "Compare LA and Santa Ana airport congestion levels."
-- Inputs for ANY set of airports: domestic airside delay (on-time), peak-hour scheduling,
-- commercial ops per runway (T-100, all carriers incl. international), total ops incl. GA (TAF history).
-- Parameter: list of airport codes (any code the airport has used).
SET VARIABLE airports = ['LAX', 'SNA'];

WITH ids AS (
    SELECT DISTINCT airport_id, current_code FROM dim_airport, unnest(all_codes) AS u(c)
    WHERE list_contains(getvariable('airports'), c)
),
ot AS (
    SELECT origin_airport_id AS airport_id,
           count(*) AS sched_deps, count(DISTINCT flight_date) AS days,
           round(100.0 * avg(cancelled), 2) AS cancel_pct,
           round(100.0 * avg(dep_del15) FILTER (WHERE cancelled = 0), 1) AS dep_delay15_pct,
           round(avg(dep_delay) FILTER (WHERE cancelled = 0), 1) AS avg_dep_delay_min,
           round(avg(taxi_out) FILTER (WHERE cancelled = 0 AND diverted = 0), 1) AS avg_taxi_out_min,
           round(100.0 * sum(nas_delay) / nullif(sum(carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay), 0), 1)
               AS nas_share_of_late_minutes_pct,
           string_agg(DISTINCT strftime(period_month, '%Y-%m'), ',' ORDER BY strftime(period_month, '%Y-%m')) AS ontime_months
    FROM v_ontime_flight WHERE origin_airport_id IN (SELECT airport_id FROM ids) GROUP BY 1
),
peak AS (   -- busiest scheduled hour: avg daily scheduled departures + arrivals in that local hour
    SELECT airport_id, max(ops_per_day) AS peak_hour_sched_ops FROM (
        SELECT airport_id, hr, count(*) / count(DISTINCT flight_date) AS ops_per_day FROM (
            SELECT origin_airport_id AS airport_id, crs_dep_hour AS hr, flight_date FROM v_ontime_flight
            UNION ALL
            SELECT dest_airport_id, crs_arr_hour, flight_date FROM v_ontime_flight) x
        WHERE airport_id IN (SELECT airport_id FROM ids) GROUP BY 1, 2) GROUP BY 1
),
t100 AS (
    SELECT origin_airport_id AS airport_id, sum(departures_performed)::BIGINT AS t100_deps_cy2025,
           round(100.0 * sum(departures_performed) FILTER (WHERE is_international) / sum(departures_performed), 1) AS intl_dep_pct
    FROM v_t100_segment WHERE year = 2025 AND origin_airport_id IN (SELECT airport_id FROM ids) GROUP BY 1
),
taf AS (
    SELECT airport_id, max(total_ops) FILTER (WHERE fiscal_year = 2024) AS taf_total_ops_fy2024,
           max(itn_ga + loc_ga) FILTER (WHERE fiscal_year = 2024) AS taf_ga_ops_fy2024
    FROM v_taf_operations WHERE record_type = 'historical' AND airport_id IN (SELECT airport_id FROM ids) GROUP BY 1
)
SELECT ids.current_code AS code, d.runways_open, ot.ontime_months, ot.sched_deps AS ontime_sched_deps,
       ot.dep_delay15_pct, ot.avg_dep_delay_min, ot.avg_taxi_out_min, ot.cancel_pct, ot.nas_share_of_late_minutes_pct,
       round(peak.peak_hour_sched_ops, 1) AS peak_hour_sched_ops,
       t100.t100_deps_cy2025, t100.intl_dep_pct,
       round(2.0 * t100.t100_deps_cy2025 / nullif(d.runways_open, 0)) AS commercial_ops_per_runway_cy2025,
       taf.taf_total_ops_fy2024, round(100.0 * taf.taf_ga_ops_fy2024 / nullif(taf.taf_total_ops_fy2024, 0), 1) AS ga_share_pct
FROM ids
JOIN dim_airport d USING (airport_id)
LEFT JOIN ot USING (airport_id) LEFT JOIN peak USING (airport_id) LEFT JOIN t100 USING (airport_id) LEFT JOIN taf USING (airport_id)
ORDER BY code;

-- Documented non-delay constraints for the same airports (cited, with verification status)
SELECT airport_iata AS code, category, item, value, unit, status, verification
FROM curated_constraint
WHERE list_contains(getvariable('airports'), airport_iata) AND category IN ('regulatory_cap', 'curfew', 'capacity_rate', 'runway_geometry')
ORDER BY code, category, item;
