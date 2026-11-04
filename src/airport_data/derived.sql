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
