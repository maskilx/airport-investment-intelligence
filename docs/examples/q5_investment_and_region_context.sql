-- Q5 validation case (Phase 1.1 sources): investment & regional context for any Census division.
-- Shows the new data joins through the identity layer: FAA grants (awarded $), NPIAS (planned NEED estimate),
-- ATADS tower operations (all users), BEA metro population/income growth. Inputs only — no scoring.
SET VARIABLE division = 'New England';

WITH apt AS (
    SELECT d.airport_id, d.current_code, d.state_abr FROM dim_airport d
    JOIN dim_airport_faa f USING (airport_id)
    WHERE d.census_division = getvariable('division') AND f.faa_hub_class IN ('L', 'M', 'S', 'N')
),
grants AS (
    SELECT airport_id, sum(amount_usd) FILTER (WHERE status = 'awarded') AS grants_awarded_fy21_25_usd,
           sum(amount_usd) FILTER (WHERE status = 'awarded' AND description ILIKE '%terminal%') AS terminal_related_awarded_usd
    FROM v_airport_investment_records WHERE record_type = 'faa_grant' GROUP BY 1
),
npias AS (
    SELECT airport_id, max(amount_usd) AS npias_2025_29_need_estimate_usd
    FROM v_airport_investment_records WHERE record_type = 'npias_development_estimate' GROUP BY 1
),
ops AS (
    SELECT airport_id, sum(total_operations) FILTER (WHERE fiscal_year = 2025) AS atads_ops_fy2025,
           sum(total_operations) FILTER (WHERE fiscal_year = 2024) AS atads_ops_fy2024,
           count(*) FILTER (WHERE fiscal_year = 2025) AS fy2025_months
    FROM v_atads_airport_ops GROUP BY 1
),
econ AS (
    SELECT airport_id, any_value(cbsa_title) AS cbsa_title,
           max(cbsa_population) FILTER (WHERE year = 2024) AS cbsa_pop_2024,
           max(cbsa_population) FILTER (WHERE year = 2014) AS cbsa_pop_2014,
           max(cbsa_per_capita_income_usd) FILTER (WHERE year = 2024) AS cbsa_pc_income_2024
    FROM v_airport_area_econ GROUP BY 1
)
SELECT a.current_code AS code, a.state_abr AS st, econ.cbsa_title,
       round(grants.grants_awarded_fy21_25_usd / 1e6, 1) AS grants_awarded_fy21_25_musd,
       round(grants.terminal_related_awarded_usd / 1e6, 1) AS terminal_text_grants_musd,
       round(npias.npias_2025_29_need_estimate_usd / 1e6, 1) AS npias_need_estimate_musd,
       ops.atads_ops_fy2025, CASE WHEN ops.fy2025_months = 12 THEN round(100.0 * (ops.atads_ops_fy2025 / ops.atads_ops_fy2024 - 1), 1) END AS ops_yoy_pct,
       econ.cbsa_pop_2024::BIGINT AS cbsa_pop_2024,
       round(100.0 * (econ.cbsa_pop_2024 / econ.cbsa_pop_2014 - 1), 1) AS cbsa_pop_growth_10y_pct,
       round(econ.cbsa_pc_income_2024) AS cbsa_per_capita_income_2024
FROM apt a
LEFT JOIN grants USING (airport_id) LEFT JOIN npias USING (airport_id) LEFT JOIN ops USING (airport_id) LEFT JOIN econ USING (airport_id)
ORDER BY npias.npias_2025_29_need_estimate_usd DESC NULLS LAST;
