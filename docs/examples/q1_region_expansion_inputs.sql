-- Q1 validation case: "Which airports in New England are strong candidates for terminal expansion?"
-- Phase 1 scope: prove the INPUTS exist and join for any region. No scoring here.
-- Parameter: any Census division (or swap the filter for state list / FAA region).
SET VARIABLE division = 'New England';

WITH latest AS (SELECT max(period_month) AS m FROM v_t100_segment),
t12 AS (   -- trailing 12 months vs the 12 before, keyed by stable airport_id
    SELECT origin_airport_id AS airport_id,
           sum(passengers) FILTER (WHERE period_month >  l.m - INTERVAL 12 MONTH)                                    AS pax_t12,
           sum(passengers) FILTER (WHERE period_month <= l.m - INTERVAL 12 MONTH AND period_month > l.m - INTERVAL 24 MONTH) AS pax_p12,
           sum(seats)      FILTER (WHERE period_month >  l.m - INTERVAL 12 MONTH)                                    AS seats_t12,
           sum(departures_performed) FILTER (WHERE period_month > l.m - INTERVAL 12 MONTH)                           AS deps_t12
    FROM v_t100_segment, latest l
    WHERE service_type IN ('passenger', 'combi')
    GROUP BY 1
),
enp AS (
    SELECT airport_id, max(enplanements) FILTER (WHERE cy = 2025) AS enp_cy2025,
                       max(enplanements) FILTER (WHERE cy = 2024) AS enp_cy2024, max(hub) FILTER (WHERE cy = 2025) AS hub
    FROM v_faa_enplanements_annual GROUP BY 1
),
taf AS (   -- FAA TAF total enplanements (domestic + international), FISCAL years
    SELECT airport_id, sum(total_enplanements) FILTER (WHERE fiscal_year = 2025) AS taf_fy2025,
                       sum(total_enplanements) FILTER (WHERE fiscal_year = 2035) AS taf_fy2035
    FROM v_taf_enplanements GROUP BY 1
),
proj AS (
    SELECT airport_iata, count(*) AS curated_rows,
           count(*) FILTER (WHERE category IN ('terminal_project', 'master_plan')) AS terminal_or_plan_rows
    FROM curated_constraint GROUP BY 1
)
SELECT d.current_code AS code, d.state_abr AS st, enp.hub,
       enp.enp_cy2025, round(100.0 * (enp.enp_cy2025 / enp.enp_cy2024 - 1), 1)  AS enp_yoy_pct,
       t12.pax_t12::BIGINT AS t100_pax_t12, round(100.0 * (t12.pax_t12 / nullif(t12.pax_p12, 0) - 1), 1) AS t100_pax_yoy_pct,
       round(100.0 * t12.pax_t12 / nullif(t12.seats_t12, 0), 1)               AS seat_factor_t12_pct,
       round(100.0 * (taf.taf_fy2035 / nullif(taf.taf_fy2025, 0) - 1), 1)       AS taf_growth_fy25_35_pct,
       d.runways_open, d.longest_runway_ft, coalesce(proj.terminal_or_plan_rows, 0) AS curated_terminal_rows
FROM dim_airport d
JOIN enp USING (airport_id)
LEFT JOIN t12 USING (airport_id)
LEFT JOIN taf USING (airport_id)
LEFT JOIN proj ON proj.airport_iata = d.current_code
WHERE d.census_division = getvariable('division') AND enp.enp_cy2025 >= 10000
ORDER BY enp.enp_cy2025 DESC;
