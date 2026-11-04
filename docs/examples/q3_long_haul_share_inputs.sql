-- Q3 validation case: "What percentage of flights out of Anchorage are long-haul flights?"
-- The answer depends on definitions, so the data must support every reasonable one:
-- service type (passenger / freight / combi / all) x distance threshold (statute miles).
-- Parameters: airport code(s) and thresholds. Window: trailing 12 months of available T-100.
SET VARIABLE airports = ['ANC'];
SET VARIABLE thresholds = [2000, 3000, 3500];

WITH latest AS (SELECT max(period_month) AS m FROM v_t100_segment),
ids AS (SELECT DISTINCT airport_id FROM dim_airport, unnest(all_codes) u(c) WHERE list_contains(getvariable('airports'), c)),
base AS (
    SELECT t.service_type, t.distance, t.departures_performed, t.is_international, t.period_month
    FROM v_t100_segment t, latest l
    WHERE t.origin_airport_id IN (SELECT airport_id FROM ids) AND t.period_month > l.m - INTERVAL 12 MONTH
      AND t.departures_performed > 0
),
scopes AS (
    SELECT 'all' AS scope, * FROM base
    UNION ALL SELECT service_type, * FROM base WHERE service_type IN ('passenger', 'freight', 'combi')
)
SELECT scope, th AS min_miles,
       strftime(min(period_month), '%Y-%m') || '..' || strftime(max(period_month), '%Y-%m') AS window,
       sum(departures_performed)::BIGINT AS departures,
       sum(departures_performed) FILTER (WHERE distance >= th)::BIGINT AS long_haul_departures,
       round(100.0 * sum(departures_performed) FILTER (WHERE distance >= th) / sum(departures_performed), 1) AS long_haul_pct,
       round(100.0 * sum(departures_performed) FILTER (WHERE is_international) / sum(departures_performed), 1) AS intl_pct
FROM scopes, unnest(getvariable('thresholds')) AS u(th)
GROUP BY scope, th
ORDER BY CASE scope WHEN 'all' THEN 0 WHEN 'passenger' THEN 1 WHEN 'freight' THEN 2 ELSE 3 END, th;
