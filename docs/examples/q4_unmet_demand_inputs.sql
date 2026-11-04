-- Q4 validation case: "What is the unmet flight demand at SFO, and what factors contribute to it?"
-- Unmet demand is NOT observable. Phase 1 proves the indicator inputs and the inputs a later
-- estimation step (e.g. a spill model) needs are present for ANY airport.
SET VARIABLE airports = ['SFO'];

-- (a) Monthly supply/traffic, domestic vs international — seat factor pressure over time
WITH ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c))
SELECT strftime(period_month, '%Y-%m') AS month,
       sum(seats)::BIGINT AS seats, sum(passengers)::BIGINT AS pax,
       round(100.0 * sum(passengers) / sum(seats), 1) AS seat_factor_pct,
       round(100.0 * sum(passengers) FILTER (WHERE is_international) / nullif(sum(seats) FILTER (WHERE is_international), 0), 1) AS intl_seat_factor_pct,
       sum(departures_performed)::BIGINT AS deps
FROM v_t100_segment
WHERE origin_airport_id IN (SELECT airport_id FROM ids) AND service_type IN ('passenger', 'combi') AND seats > 0
GROUP BY 1 ORDER BY 1;

-- (b) Route-level inputs for a spill estimate: distribution of route-month seat factors (trailing 12 months)
WITH ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c)),
latest AS (SELECT max(period_month) AS m FROM v_t100_segment),
rm AS (
    SELECT dest, period_month, sum(passengers) AS pax, sum(seats) AS seats
    FROM v_t100_segment, latest l
    WHERE origin_airport_id IN (SELECT airport_id FROM ids) AND service_type IN ('passenger', 'combi')
      AND seats > 0 AND period_month > l.m - INTERVAL 12 MONTH
    GROUP BY 1, 2
)
SELECT count(*) AS route_months, count(DISTINCT dest) AS routes,
       count(*) FILTER (WHERE pax / seats >= 0.85) AS route_months_sf_ge_85,
       round(100.0 * sum(pax) FILTER (WHERE pax / seats >= 0.85) / sum(pax), 1) AS pax_share_on_sf_ge_85_pct,
       round(quantile_cont(pax / seats, 0.5) * 100, 1) AS median_route_month_sf_pct,
       round(quantile_cont(pax / seats, 0.9) * 100, 1) AS p90_route_month_sf_pct
FROM rm;

-- (c) Operational drivers: delay causes and hourly scheduled demand (on-time, domestic reporting carriers)
WITH ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c))
SELECT strftime(period_month, '%Y-%m') AS month,
       count(*) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids)) AS sched_arrivals,
       round(100.0 * avg(arr_del15) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids) AND cancelled = 0 AND diverted = 0), 1) AS arr_delay15_pct,
       round(100.0 * sum(weather_delay) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids))
             / nullif(sum(carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids)), 0), 1) AS weather_share_late_min_pct,
       round(100.0 * sum(nas_delay) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids))
             / nullif(sum(carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay) FILTER (WHERE dest_airport_id IN (SELECT airport_id FROM ids)), 0), 1) AS nas_share_late_min_pct
FROM v_ontime_flight
WHERE dest_airport_id IN (SELECT airport_id FROM ids) OR origin_airport_id IN (SELECT airport_id FROM ids)
GROUP BY 1 ORDER BY 1;

-- (d) Peak scheduled hourly operations vs documented (modeled) capacity rates
WITH ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c)),
hourly AS (
    SELECT hr, count(*) / count(DISTINCT flight_date) AS avg_sched_ops FROM (
        SELECT crs_dep_hour AS hr, flight_date FROM v_ontime_flight WHERE origin_airport_id IN (SELECT airport_id FROM ids)
        UNION ALL
        SELECT crs_arr_hour, flight_date FROM v_ontime_flight WHERE dest_airport_id IN (SELECT airport_id FROM ids)) GROUP BY 1
)
SELECT 'observed: top scheduled hour (domestic reporting carriers only)' AS what, max(round(avg_sched_ops, 1))::VARCHAR AS value,
       'ops/hour' AS unit, 'bts_ontime' AS source FROM hourly
UNION ALL
SELECT item, value, unit, verification FROM curated_constraint
WHERE list_contains(getvariable('airports'), airport_iata) AND category IN ('capacity_rate', 'runway_geometry', 'other');

-- (e) Forecast demand context (FAA TAF, fiscal years)
WITH ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c))
SELECT fiscal_year, record_type, total_enplanements::BIGINT AS taf_total_enplanements,
       domestic_enplanements::BIGINT AS taf_domestic, international_enplanements::BIGINT AS taf_international
FROM v_taf_enplanements WHERE airport_id IN (SELECT airport_id FROM ids) AND fiscal_year IN (2019, 2024, 2025, 2030, 2035, 2045)
ORDER BY fiscal_year;
