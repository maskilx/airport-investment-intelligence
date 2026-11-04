-- Conformed layer: generic, question-agnostic views/dimensions over the source tables.
-- Semantics only (code decoding, keys, units, time) — no analytics, scoring or estimation.

-- ---------------------------------------------------------------- airport identity
-- The stable airport key is BTS AIRPORT_ID. 3-letter codes change over time (e.g. Palm Beach:
-- PBI -> DJT, same AIRPORT_ID 14027), and FAA LIDs differ from IATA codes (GPI vs FCA, IWA vs AZA).
-- Time series must therefore group by airport_id, never by code.
CREATE OR REPLACE TABLE airport_code_history AS
WITH obs AS (
    SELECT origin_airport_id AS airport_id, origin AS code, _period AS period, 'bts_t100_segment' AS src,
           origin_country AS country, origin_state_abr AS state_abr, origin_city_name AS city_name FROM t100_segment
    UNION ALL
    SELECT dest_airport_id, dest, _period, 'bts_t100_segment', dest_country, dest_state_abr, dest_city_name FROM t100_segment
    UNION ALL
    SELECT origin_airport_id, origin, _period, 'bts_ontime', NULL, origin_state, origin_city_name FROM ontime_flight
    UNION ALL
    SELECT dest_airport_id, dest, _period, 'bts_ontime', NULL, dest_state, dest_city_name FROM ontime_flight
)
SELECT CAST(airport_id AS INTEGER) AS airport_id, code, min(period) AS first_period, max(period) AS last_period,
       list(DISTINCT src ORDER BY src) AS seen_in,
       -- deterministic attribute choice: latest period, T-100 before on-time, then value order
       coalesce(arg_max(country, period || '|' || src || '|' || country) FILTER (WHERE country IS NOT NULL), 'US') AS country,
       arg_max(state_abr, period || '|' || src || '|' || coalesce(state_abr, '')) AS state_abr,
       arg_max(city_name, period || '|' || src || '|' || coalesce(city_name, '')) AS city_name
FROM obs WHERE airport_id IS NOT NULL GROUP BY airport_id, code;

-- OurAirports candidates: match a BTS code via IATA, then FAA LID, then ICAO (K/P + code)
CREATE OR REPLACE TABLE airport_oa_match AS
WITH cur AS (
    SELECT airport_id, code, country, state_abr,
           row_number() OVER (PARTITION BY airport_id ORDER BY last_period DESC, first_period DESC, code) AS recency
    FROM airport_code_history
), cand AS (
    SELECT c.airport_id, c.recency, a.id AS oa_id, m.rule,
           CASE a.type WHEN 'large_airport' THEN 1 WHEN 'medium_airport' THEN 2 WHEN 'small_airport' THEN 3 ELSE 4 END AS size_rk
    FROM cur c
    JOIN oa_airport a ON a.type <> 'closed'
    JOIN (VALUES (1, 'iata'), (2, 'faa_lid'), (3, 'icao')) m(prio, rule) ON (
         (m.rule = 'iata' AND a.iata_code = c.code AND ((c.country = 'US' AND a.iso_country IN ('US','PR','VI','GU','AS','MP')) OR (c.country <> 'US' AND a.iso_country = c.country)))
      OR (m.rule = 'faa_lid' AND c.country = 'US' AND a.local_code = c.code AND a.iso_country IN ('US','PR','VI','GU','AS','MP'))
      OR (m.rule = 'icao' AND c.country = 'US' AND a.ident IN ('K' || c.code, 'P' || c.code, 'T' || c.code)
          AND coalesce(a.iata_code, '') IN ('', c.code)))   -- guard: never steal an airport that has another IATA code
)
SELECT airport_id, oa_id, rule FROM cand
QUALIFY row_number() OVER (PARTITION BY airport_id ORDER BY recency,
        CASE rule WHEN 'iata' THEN 1 WHEN 'faa_lid' THEN 2 ELSE 3 END, size_rk, oa_id) = 1;

CREATE OR REPLACE TABLE dim_airport AS
WITH cur AS (
    SELECT airport_id, code AS current_code, country, state_abr AS bts_state_abr, city_name
    FROM airport_code_history
    QUALIFY row_number() OVER (PARTITION BY airport_id ORDER BY last_period DESC, first_period DESC, code) = 1
), codes AS (
    SELECT airport_id, list(code ORDER BY first_period, code) AS all_codes FROM airport_code_history GROUP BY 1
), rw AS (
    SELECT airport_ref, count(*) AS runways_open, max(length_ft) AS longest_runway_ft,
           count(*) FILTER (WHERE length_ft >= 7000) AS runways_7000ft_plus
    FROM oa_runway WHERE NOT closed GROUP BY 1
), lk AS (
    SELECT CAST(code AS INTEGER) AS airport_id, description FROM bts_lookup WHERE lookup = 'L_AIRPORT_ID'
)
SELECT cur.airport_id, cur.current_code, codes.all_codes, cur.country,
       nullif(a.iata_code, '') AS oa_iata, nullif(a.local_code, '') AS faa_lid, nullif(a.gps_code, '') AS icao,
       coalesce(a.name, split_part(lk.description, ': ', 2)) AS name, lk.description AS bts_description, cur.city_name,
       coalesce(CASE WHEN a.iso_country = 'US' THEN split_part(a.iso_region, '-', 2) END, cur.bts_state_abr) AS state_abr,
       s.state_name, s.census_region, s.census_division,
       a.type AS oa_type, a.scheduled_service = 'yes' AS oa_scheduled_service,
       a.latitude_deg, a.longitude_deg, a.elevation_ft, m.rule AS oa_match_rule,
       rw.runways_open, rw.longest_runway_ft, rw.runways_7000ft_plus
FROM cur
JOIN codes USING (airport_id)
LEFT JOIN lk USING (airport_id)
LEFT JOIN airport_oa_match m USING (airport_id)
LEFT JOIN oa_airport a ON a.id = m.oa_id
LEFT JOIN rw ON rw.airport_ref = a.id
LEFT JOIN ref_us_state s ON s.state_abr = coalesce(CASE WHEN a.iso_country = 'US' THEN split_part(a.iso_region, '-', 2) END, cur.bts_state_abr);

-- FAA (LID-keyed) attributes joined onto the BTS identity
CREATE OR REPLACE TABLE dim_airport_faa AS
WITH enp AS (SELECT locid, hub, s_l, cy FROM faa_enplanements QUALIFY row_number() OVER (PARTITION BY locid ORDER BY cy DESC, hub) = 1)
SELECT d.airport_id, d.faa_lid, enp.hub AS faa_hub_class, enp.s_l AS faa_service_level, enp.cy AS faa_hub_class_cy,
       t.region AS faa_region, t.hub_size AS taf_hub_size_code, t.atct_flag AS taf_atct_flag
FROM dim_airport d
LEFT JOIN enp ON enp.locid = d.faa_lid
LEFT JOIN taf_airport t ON t.locid = d.faa_lid
WHERE d.faa_lid IS NOT NULL;

-- Crosswalk: FAA LID -> BTS airport_id (for FAA-keyed tables: enplanements, cargo, TAF)
-- Also resolves *historical* codes (FY2025 TAF still files Palm Beach as PBI; ACAIS CY2025 uses DJT).
CREATE OR REPLACE VIEW xref_faa_lid AS
WITH cand AS (
    SELECT faa_lid AS lid, airport_id, current_code, 1 AS prio FROM dim_airport WHERE faa_lid IS NOT NULL
    UNION ALL
    SELECT unnest(all_codes), airport_id, current_code, 2 FROM dim_airport WHERE country = 'US'
)
SELECT lid AS faa_lid, airport_id, current_code, CASE prio WHEN 1 THEN 'faa_lid' ELSE 'bts_code_history' END AS match_rule
FROM cand
QUALIFY row_number() OVER (PARTITION BY lid ORDER BY prio, airport_id) = 1;

-- ---------------------------------------------------------------- T-100 semantic view
CREATE OR REPLACE VIEW v_t100_segment AS
SELECT t.*,
       make_date(CAST(t.year AS INTEGER), CAST(t.month AS INTEGER), 1)                               AS period_month,
       cfg.description                                             AS aircraft_config_desc,
       CASE t.aircraft_config WHEN 1 THEN 'passenger' WHEN 2 THEN 'freight' WHEN 3 THEN 'combi'
                              WHEN 4 THEN 'seaplane' ELSE 'other' END AS service_type,
       cls.description                                             AS class_desc,
       t.class IN ('F', 'G')                                       AS is_scheduled,
       (t.origin_country <> 'US' OR t.dest_country <> 'US')        AS is_international
FROM t100_segment t
LEFT JOIN bts_lookup cfg ON cfg.lookup = 'L_AIRCRAFT_CONFIG' AND cfg.code = CAST(t.aircraft_config AS VARCHAR)
LEFT JOIN bts_lookup cls ON cls.lookup = 'L_SERVICE_CLASS' AND cls.code = t.class
WHERE t.origin <> t.dest;            -- self-loop rows excluded (counted in validation warnings)

-- ---------------------------------------------------------------- On-time semantic view
CREATE OR REPLACE VIEW v_ontime_flight AS
SELECT f.*,
       TRY_CAST(substr(lpad(CAST(f.crs_dep_time AS VARCHAR), 4, '0'), 1, 2) AS INTEGER) % 24 AS crs_dep_hour,
       TRY_CAST(substr(lpad(CAST(f.crs_arr_time AS VARCHAR), 4, '0'), 1, 2) AS INTEGER) % 24 AS crs_arr_hour,
       make_date(CAST(f.year AS INTEGER), CAST(f.month AS INTEGER), 1)                                       AS period_month
FROM ontime_flight f;

-- ---------------------------------------------------------------- FAA enplanements, one row per airport x CY
-- A CY's value is taken from its own workbook when available, else from the next CY's "prior year" column.
CREATE OR REPLACE VIEW v_faa_enplanements_annual AS
WITH longf AS (
    SELECT locid, st, hub, cy, value_cy AS enplanements, 'own_workbook' AS basis, cy AS workbook_cy, _vintage_id FROM faa_enplanements
    UNION ALL
    SELECT locid, st, hub, cy - 1, value_prior_cy, 'next_workbook_prior_column', cy, _vintage_id FROM faa_enplanements
)
SELECT e.* EXCLUDE (rk, current_code), e.current_code AS bts_code FROM (
    SELECT l.*, x.airport_id, x.current_code,
           row_number() OVER (PARTITION BY coalesce(CAST(x.airport_id AS VARCHAR), 'LID:' || l.locid), l.cy
                              ORDER BY l.basis = 'own_workbook' DESC, l.workbook_cy DESC, l.locid) AS rk
    FROM longf l LEFT JOIN xref_faa_lid x ON x.faa_lid = l.locid
    WHERE l.enplanements IS NOT NULL) e
WHERE rk = 1;   -- one row per airport x CY even if the airport's LID changed (PBI -> DJT)

CREATE OR REPLACE VIEW v_faa_cargo_annual AS
WITH longf AS (
    SELECT locid, st, cy, value_cy AS landed_weight_lbs, 'own_workbook' AS basis, cy AS workbook_cy FROM faa_cargo
    UNION ALL
    SELECT locid, st, cy - 1, value_prior_cy, 'next_workbook_prior_column', cy FROM faa_cargo
)
SELECT e.* EXCLUDE (rk, current_code), e.current_code AS bts_code FROM (
    SELECT l.*, x.airport_id, x.current_code,
           row_number() OVER (PARTITION BY coalesce(CAST(x.airport_id AS VARCHAR), 'LID:' || l.locid), l.cy
                              ORDER BY l.basis = 'own_workbook' DESC, l.workbook_cy DESC, l.locid) AS rk
    FROM longf l LEFT JOIN xref_faa_lid x ON x.faa_lid = l.locid
    WHERE l.landed_weight_lbs IS NOT NULL) e
WHERE rk = 1;   -- one row per airport x CY even if the airport's LID changed (PBI -> DJT)

-- ---------------------------------------------------------------- TAF (fiscal years!)
CREATE OR REPLACE VIEW v_taf_enplanements AS
-- Column semantics (inferred, then verified: FY2024 total vs FAA CY2024 boardings, median ratio 0.994
-- over 102 airports >1M): aac + aat + commuter = DOMESTIC; us_flag + frgn_flag = INTERNATIONAL (additive).
SELECT e.*, CASE e.scenario WHEN 0 THEN 'historical' WHEN 1 THEN 'forecast' END AS record_type,
       (e._period)::INTEGER AS taf_release_year, x.airport_id, x.current_code AS bts_code,
       e.aac + e.aat + e.commuter                               AS domestic_enplanements,
       e.us_flag + e.frgn_flag                                  AS international_enplanements,
       coalesce(e.aac,0) + coalesce(e.aat,0) + coalesce(e.commuter,0) + coalesce(e.us_flag,0) + coalesce(e.frgn_flag,0) AS total_enplanements
FROM taf_enplanements e LEFT JOIN xref_faa_lid x ON x.faa_lid = e.locid;

CREATE OR REPLACE VIEW v_taf_operations AS
SELECT o.*, CASE o.scenario WHEN 0 THEN 'historical' WHEN 1 THEN 'forecast' END AS record_type,
       (o._period)::INTEGER AS taf_release_year, x.airport_id, x.current_code AS bts_code,
       coalesce(o.itn_ac,0) + coalesce(o.itn_at,0) + coalesce(o.itn_ga,0) + coalesce(o.itn_mil,0) + coalesce(o.loc_ga,0) + coalesce(o.loc_mil,0) AS total_ops
FROM taf_operations o LEFT JOIN xref_faa_lid x ON x.faa_lid = o.locid;

-- ---------------------------------------------------------------- freshness (relative to today)
CREATE OR REPLACE VIEW v_source_freshness AS
WITH sel AS (
    SELECT source_id, max(period) AS latest_period, count(*) AS periods_loaded, min(period) AS first_period
    FROM ingest_manifest WHERE selected GROUP BY 1
), exp AS (
    SELECT c.id AS source_id, c.period_kind, c.cadence, c.expected_lag_days,
           current_date - c.expected_lag_days * INTERVAL 1 DAY AS horizon
    FROM source_catalog c
)
SELECT e.source_id, e.period_kind, e.cadence, s.first_period, s.latest_period, s.periods_loaded,
       CASE e.period_kind
           WHEN 'month' THEN strftime(e.horizon - INTERVAL 1 MONTH, '%Y-%m')
           WHEN 'year' THEN CAST(year(e.horizon) - 1 AS VARCHAR)
           WHEN 'version' THEN NULL
           WHEN 'snapshot' THEN NULL END AS expected_latest_period,
       CASE
           WHEN s.latest_period IS NULL THEN 'MISSING'
           WHEN e.period_kind = 'month' AND s.latest_period < strftime(e.horizon - INTERVAL 2 MONTH, '%Y-%m') THEN 'STALE'
           WHEN e.period_kind = 'year' AND s.latest_period < CAST(year(e.horizon) - 1 AS VARCHAR) THEN 'STALE'
           WHEN e.period_kind = 'snapshot' AND TRY_CAST(s.latest_period AS DATE) < current_date - INTERVAL 120 DAY THEN 'STALE'
           ELSE 'OK' END AS freshness
FROM exp e LEFT JOIN sel s USING (source_id);

-- ---------------------------------------------------------------- period completeness: missing != zero
-- One row per expected period for every monthly/annual source, from its first loaded period up to the
-- period the publisher should have released by now (cadence + lag). status:
--   loaded            a validated vintage is in the DB
--   missing           expected but absent (gap, failed fetch, or rejected vintage) -> treat as UNKNOWN, never 0
--   not_yet_expected  inside the publication lag (normal)
CREATE OR REPLACE VIEW v_source_period_status AS
WITH loaded AS (
    SELECT source_id, period FROM ingest_manifest WHERE selected GROUP BY ALL
), cat AS (
    SELECT id AS source_id, period_kind, period_basis, expected_lag_days FROM source_catalog WHERE period_kind IN ('month', 'year')
), bounds AS (
    SELECT c.source_id, c.period_kind, c.period_basis, min(l.period) AS first_period, max(l.period) AS last_loaded,
           current_date - c.expected_lag_days * INTERVAL 1 DAY AS horizon
    FROM cat c JOIN loaded l USING (source_id) GROUP BY ALL
), spine AS (
    SELECT b.source_id, b.period_kind, strftime(m, '%Y-%m') AS period, m <= b.horizon - INTERVAL 1 MONTH AS expected
    FROM bounds b, generate_series(CAST(b.first_period || '-01' AS DATE),
                                   greatest(CAST(b.last_loaded || '-01' AS DATE), CAST(date_trunc('month', current_date) AS DATE)),
                                   INTERVAL 1 MONTH) AS g(m)
    WHERE b.period_kind = 'month'
    UNION ALL
    SELECT b.source_id, b.period_kind, CAST(y AS VARCHAR),
           -- calendar year Y is due after Dec 31 + lag; federal fiscal year Y after Sep 30 of Y + lag
           CASE WHEN b.period_basis = 'fiscal' THEN make_date(y, 9, 30) <= b.horizon ELSE y <= year(b.horizon) - 1 END
    FROM bounds b, generate_series(CAST(b.first_period AS INTEGER), greatest(CAST(b.last_loaded AS INTEGER), year(current_date))) AS g(y)
    WHERE b.period_kind = 'year'
)
SELECT s.source_id, s.period_kind, s.period,
       CASE WHEN l.period IS NOT NULL THEN 'loaded' WHEN s.expected THEN 'missing' ELSE 'not_yet_expected' END AS status
FROM spine s LEFT JOIN loaded l ON l.source_id = s.source_id AND l.period = s.period;

-- Airport x month activity per traffic source. 0 = source month loaded and no activity;
-- NULL = the source month is not in the DB (unknown). Never coalesce NULL to 0 downstream.
CREATE OR REPLACE VIEW v_airport_month_activity AS
WITH months AS (
    SELECT source_id, period, CAST(period || '-01' AS DATE) AS month, status
    FROM v_source_period_status WHERE source_id IN ('bts_t100_segment', 'bts_ontime', 'faa_atads_ops')
), t100 AS (
    SELECT origin_airport_id AS airport_id, _period AS period, sum(departures_performed) AS deps, sum(passengers) AS pax
    FROM t100_segment GROUP BY ALL
), ot AS (
    SELECT origin_airport_id AS airport_id, _period AS period, count(*) FILTER (WHERE cancelled = 0) AS deps,
           NULL::DOUBLE AS pax
    FROM ontime_flight GROUP BY ALL            -- operated (not cancelled) reporting-carrier departures
), atads AS (
    SELECT x.airport_id, a._period AS period, sum(a.total_operations) AS deps, NULL::DOUBLE AS pax
    FROM atads_airport_ops a JOIN xref_faa_lid x ON x.faa_lid = a.locid GROUP BY ALL   -- tower OPERATIONS, not departures
)
-- activity = T-100 departures performed | On-Time operated departures | ATADS tower operations (arr+dep, all users).
-- For ATADS, 0 is only meaningful for towered airports; non-towered airports are excluded below.
SELECT d.airport_id, d.current_code, m.source_id, m.month, m.status AS source_month_status,
       CASE m.source_id WHEN 'faa_atads_ops' THEN 'tower_operations' ELSE 'departures' END AS activity_measure,
       CASE WHEN m.status = 'loaded' THEN coalesce(x.deps, 0) END AS activity,
       CASE WHEN m.status = 'loaded' AND m.source_id = 'bts_t100_segment' THEN coalesce(x.pax, 0) END AS passengers
FROM dim_airport d
CROSS JOIN months m
LEFT JOIN (SELECT 'bts_t100_segment' AS source_id, * FROM t100 UNION ALL SELECT 'bts_ontime', * FROM ot
           UNION ALL SELECT 'faa_atads_ops', * FROM atads) x
       ON x.airport_id = d.airport_id AND x.period = m.period AND x.source_id = m.source_id
WHERE d.country = 'US'
  AND (m.source_id <> 'faa_atads_ops' OR d.airport_id IN (SELECT x.airport_id FROM atads_airport_ops a JOIN xref_faa_lid x ON x.faa_lid = a.locid));

-- ---------------------------------------------------------------- FAA ATADS (tower operations) — NOT the same as BTS flights
CREATE OR REPLACE VIEW v_atads_airport_ops AS
SELECT a.*, make_date(a.year, a.month, 1) AS period_month,
       CASE WHEN a.month >= 10 THEN a.year + 1 ELSE a.year END AS fiscal_year,
       x.airport_id, x.current_code AS bts_code
FROM atads_airport_ops a LEFT JOIN xref_faa_lid x ON x.faa_lid = a.locid;

-- ---------------------------------------------------------------- infrastructure investment records
-- Different record types are NOT additive: awarded grants (money obligated), NPIAS need estimates
-- (planning figures), curated projects (documented plans/works). Never sum amount across record_type.
CREATE OR REPLACE VIEW v_faa_grant AS
SELECT g.*, x.airport_id, x.current_code AS bts_code FROM faa_grant g LEFT JOIN xref_faa_lid x ON x.faa_lid = g.locid;

CREATE OR REPLACE VIEW v_airport_investment_records AS
-- status domain: awarded | announced | planned_need_estimate | proposed | planned | under_construction | completed | in_effect
SELECT 'faa_grant' AS record_type, CASE WHEN g.award_date IS NULL THEN 'announced' ELSE 'awarded' END AS status, g.airport_id, g.locid, g.fiscal_year,
       g.award_date AS record_date, g.total_amount AS amount_usd, g.project_summary AS description,
       g.grant_number AS record_key, 'faa_grants' AS source_id, g._vintage_id
FROM v_faa_grant g
UNION ALL
SELECT 'npias_development_estimate', 'planned_need_estimate', x.airport_id, n.locid, NULL,
       NULL, n.development_estimate, 'NPIAS ' || n.npias_cycle || ' 5-year AIP-eligible development estimate (role: ' ||
       coalesce(n.role, n.hub, '?') || ')', n.locid || ':' || n.npias_cycle, 'faa_npias', n._vintage_id
FROM npias_airport n LEFT JOIN xref_faa_lid x ON x.faa_lid = n.locid
UNION ALL
SELECT 'npias_new_airport_estimate', 'planned_need_estimate', NULL, n.locid, NULL, NULL, n.development_estimate,
       'NPIAS ' || n.npias_cycle || ' proposed new/replacement airport', n.locid || ':' || n.npias_cycle, 'faa_npias', n._vintage_id
FROM npias_new_airport n
UNION ALL
SELECT 'curated_project', c.status, x.airport_id, c.airport_iata, NULL,
       TRY_CAST(c.effective_from AS DATE), NULL, c.item || coalesce(' — ' || c.value || ' ' || c.unit, ''),
       c.airport_iata || ':' || c.item, 'curated_constraints', c._vintage_id
FROM curated_constraint c
LEFT JOIN (SELECT DISTINCT airport_id, unnest(all_codes) AS code FROM dim_airport WHERE country = 'US') x ON x.code = c.airport_iata
WHERE c.category IN ('terminal_project', 'runway_project', 'master_plan');

-- ---------------------------------------------------------------- geography & regional economy
-- County name normaliser (NASR "ST LOUIS" vs BEA "St. Louis"; suffixes differ by state).
CREATE OR REPLACE MACRO norm_county(x) AS
    regexp_replace(replace(regexp_replace(upper(coalesce(x, '')),
        ' (COUNTY|PARISH|BOROUGH|CENSUS AREA|MUNICIPALITY|CITY AND BOROUGH|CITY AND COUNTY|MUNICIPIO|\(INDEPENDENT CITY\))$', ''),
        'SAINT ', 'ST '), '[^A-Z]', '', 'g');

CREATE OR REPLACE TABLE dim_county AS
SELECT DISTINCT geofips AS county_fips,
       trim(regexp_replace(geoname, ',[^,]*$', '')) AS county_name,
       trim(replace(regexp_extract(geoname, ',\s*([A-Z]{2})\*?$', 1), '*', '')) AS state_abr,
       geoname LIKE '%+%' AS is_bea_combination_area
FROM bea_county_income WHERE right(geofips, 3) <> '000' AND left(geofips, 2) NOT IN ('00', '91', '92', '93', '94', '95', '96', '97', '98');

-- Airport -> county (FAA NASR official county) -> CBSA. match_rule documents how each link was made.
CREATE OR REPLACE TABLE xref_airport_county AS
WITH apt AS (
    SELECT d.airport_id, n.arpt_id AS faa_lid, n.county_name AS nasr_county, coalesce(nullif(n.county_assoc_state, ''), n.state_code) AS st
    FROM dim_airport d JOIN nasr_airport n ON n.arpt_id = d.faa_lid AND n.site_type_code = 'A'
), direct AS (
    SELECT a.*, c.county_fips, 'nasr_county_name' AS match_rule
    FROM apt a JOIN dim_county c ON c.state_abr = a.st AND norm_county(c.county_name) = norm_county(a.nasr_county)
), override AS ( -- airport-level geography overrides (e.g. Connecticut planning regions)
    SELECT a.*, o.county_fips, 'reference_airport_override' AS match_rule
    FROM apt a JOIN ref_airport_geo_override o ON o.faa_lid = a.faa_lid
), alias AS (    -- documented renames (data/reference/county_name_aliases.csv)
    SELECT a.*, r.county_fips, 'reference_alias' AS match_rule
    FROM apt a JOIN ref_county_name_alias r ON r.state_abr = a.st AND upper(r.nasr_county_name) = upper(a.nasr_county)
), combo AS (   -- BEA combination areas, e.g. "Albemarle + Charlottesville, VA*"
    SELECT a.*, c.county_fips, 'bea_combination_area' AS match_rule
    FROM apt a JOIN dim_county c ON c.state_abr = a.st AND c.is_bea_combination_area
         AND list_contains(list_transform(string_split(c.county_name, '+'), lambda s: norm_county(trim(s))), norm_county(a.nasr_county))
    WHERE a.airport_id NOT IN (SELECT airport_id FROM direct UNION SELECT airport_id FROM alias)
)
SELECT x.*, cb.cbsa_code, cb.cbsa_title, cb.metro_micro, cb.csa_code, cb.csa_title, cb.central_outlying
FROM (SELECT * FROM override UNION ALL SELECT * FROM direct UNION ALL SELECT * FROM alias UNION ALL SELECT * FROM combo) x
LEFT JOIN cbsa_county cb ON cb.county_fips = x.county_fips
QUALIFY row_number() OVER (PARTITION BY x.airport_id ORDER BY x.match_rule = 'reference_airport_override' DESC, x.match_rule = 'reference_alias' DESC, x.match_rule, x.county_fips) = 1;

CREATE OR REPLACE VIEW v_county_econ_annual AS
SELECT geofips AS county_fips, year,
       max(value) FILTER (WHERE line_code = 2) AS population,
       max(value) FILTER (WHERE line_code = 1) * 1000 AS personal_income_usd,      -- source unit: thousands of dollars
       max(value) FILTER (WHERE line_code = 3) AS per_capita_income_usd,
       string_agg(DISTINCT value_flag, ',') FILTER (WHERE value_flag IS NOT NULL) AS suppression_flags
FROM bea_county_income WHERE right(geofips, 3) <> '000' GROUP BY ALL;

-- CBSA totals = sum of member counties (population & income are additive; per-capita is recomputed).
CREATE OR REPLACE VIEW v_cbsa_econ_annual AS
SELECT cb.cbsa_code, any_value(cb.cbsa_title) AS cbsa_title, any_value(cb.metro_micro) AS metro_micro, e.year,
       sum(e.population) AS population, sum(e.personal_income_usd) AS personal_income_usd,
       sum(e.personal_income_usd) / nullif(sum(e.population), 0) AS per_capita_income_usd,
       count(*) AS counties, count(*) FILTER (WHERE e.population IS NULL) AS counties_missing_population
FROM cbsa_county cb JOIN v_county_econ_annual e ON e.county_fips = cb.county_fips
GROUP BY cb.cbsa_code, e.year;

-- Airport's HOME county / CBSA economy. A CBSA is an administrative proxy for the market area,
-- not a measured catchment (multi-airport regions share a CBSA; travellers cross CBSA borders).
CREATE OR REPLACE VIEW v_airport_area_econ AS
SELECT x.airport_id, d.current_code, x.county_fips, x.cbsa_code, x.cbsa_title, x.metro_micro, x.match_rule,
       c.year, c.population AS county_population, c.personal_income_usd AS county_personal_income_usd,
       m.population AS cbsa_population, m.personal_income_usd AS cbsa_personal_income_usd,
       m.per_capita_income_usd AS cbsa_per_capita_income_usd
FROM xref_airport_county x
JOIN dim_airport d USING (airport_id)
LEFT JOIN v_county_econ_annual c ON c.county_fips = x.county_fips
LEFT JOIN v_cbsa_econ_annual m ON m.cbsa_code = x.cbsa_code AND m.year = c.year;
