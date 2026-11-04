# Phase 1 — Data Foundation: Implementation, Data Model & Limitations

Status: **complete, pending review** · Date: 2026-11-04 · Owner: Claude (tech lead)
Companion: [01-data-foundation.md](01-data-foundation.md) (Phase 0 research) · Results: [examples/RESULTS.md](examples/RESULTS.md)

## 1. What the pipeline guarantees

| Requirement | Mechanism | Tested by |
|---|---|---|
| Originals preserved, never overwritten | `raw/<source>/<period>/<vintage>/` written once, files chmod read-only, `meta.json` written last as commit marker | `test_revision_creates_new_vintage_and_preserves_old`, `test_incomplete_vintage_without_meta_is_ignored` |
| Revisions become new vintages | content sha256 vs newest vintage: identical → `unchanged` event, different → new vintage with `supersedes` | `test_identical_redownload_does_not_create_vintage` |
| Corrupt downloads never stored | Content-Length check, zip CRC (`testzip`), HTML-instead-of-CSV detection, before anything touches the store | `test_truncated_zip_is_rejected_and_not_stored` |
| Failed updates keep previous data | fetch failure → `failed` event only; previous vintage keeps serving | `test_failed_fetch_keeps_previous_vintage` |
| Bad revision never replaces good data | build validates newest vintage first; on blocking failure tries the next-older one; the period is flagged if none passes | `test_invalid_revision_falls_back_to_previous_valid_vintage`, `test_period_with_no_valid_vintage_is_reported` |
| Reproducible build from validated source files | build reads only the raw archive (+ repo CSVs) → temp DB → atomic `os.replace`; no network | `test_rebuild_is_bit_for_bit_reproducible`, `test_build_is_offline`, seed build runs with sockets disabled |
| Failed build cannot damage the current DB | exception → temp file removed, old DB untouched | `test_failed_build_leaves_existing_db_intact` |
| Tamper/corruption detection at build | every vintage re-hashed against `meta.json` before load | `test_verify_detects_tampering`, `test_every_selected_raw_file_matches_its_checksum` |
| Full lineage | every source row has `_source_id, _period, _vintage_id` → `ingest_manifest` (url, request params, sha256, bytes, row counts, schema + schema hash, validation status, errors, warnings, supersedes) | `test_manifest_records_required_lineage` |
| Schema evolution | additive: new publisher columns are added; old rows get NULL | `test_additive_schema_evolution` |
| Graceful degradation | missing source → typed empty placeholder tables; all views and example queries still bind (empty results), freshness shows `MISSING` | `test_build_with_no_data_still_produces_queryable_schema` |
| Freshness is explicit | `v_source_freshness`: expected latest period from cadence + publication lag vs what is loaded → `OK / STALE / MISSING` | coverage `no_stale_or_missing_sources` |

## 2. Architecture & interfaces

```
 publishers ──► Source.fetch()  ──► integrity_errors() ──► RawStore.put()      [network; `fetch`]
                                  (fail → EventLog only)     (vintage, sha256)
 RawStore ──► Source.load() → staging ──► generic + source checks ──► promote  [offline; `build`]
                                        (ValidationReport per vintage, persisted)
 DuckDB:  source tables (+lineage) │ metadata (manifest, checks, catalog, events, build_info)
          │ conformed layer (derived.sql: dim_airport, xrefs, v_* views, freshness)
 Consumers (Phase 2+): airport_data.db.connect() — read-only; no knowledge of LLMs/UIs here
```

* **Source adapter interface** (`sources/base.py`): metadata (`id, publisher, license, period_kind,
  cadence, expected_lag_days`), `TableSpec`s (required columns, not-null, keys, row-count band,
  placeholder types), `available_periods`, `fetch`, `integrity_errors`, `load`, `checks`.
  Adding a source touches only its adapter + the registry + `config/ingest.toml`.
* **Configuration, not code**: acquisition scope in `config/ingest.toml`; coverage requirements in
  `config/coverage.toml`; curated facts and reference lists as CSVs ingested through the same raw store.
* **Dependencies**: `duckdb`, `openpyxl`, `certifi` (CA bundle for urllib). Stdlib HTTP. No framework.
  LangChain/LangGraph/FastAPI/Langfuse were deliberately *not* introduced: nothing in Phase 1 needs them,
  and the read-only DB + views boundary lets any of them be added later without touching ingestion.

## 3. Data model (DuckDB)

**Source tables** (one per `TableSpec`; columns = publisher columns in snake_case + lineage):
`t100_segment`, `ontime_flight`, `bts_lookup`, `faa_enplanements`, `faa_cargo`, `taf_airport`,
`taf_enplanements`, `taf_operations`, `taf_based_aircraft`, `taf_tracon`, `oa_airport`, `oa_runway`,
`ref_us_state`, `curated_constraint`.

**Metadata**: `ingest_manifest`, `validation_check`, `source_catalog`, `table_catalog`, `fetch_events`, `build_info`.

**Conformed layer** (`derived.sql`, semantics only — no analytics):

| Object | Purpose |
|---|---|
| `airport_code_history` | every (BTS `airport_id`, code) pair with first/last period seen |
| `dim_airport` | one row per BTS `airport_id`: current code, all codes, name, state, Census region/division, coordinates, runway inventory, OurAirports match rule |
| `dim_airport_faa` | FAA hub class / service level / region / ATCT flag per airport |
| `xref_faa_lid` | FAA LID (and historical BTS codes) → `airport_id`, for FAA-keyed tables |
| `v_t100_segment` | decoded aircraft config → `service_type` (passenger/freight/combi), service class, `is_international`, `period_month`; self-loops excluded |
| `v_ontime_flight` | `crs_dep_hour`, `crs_arr_hour`, `period_month` |
| `v_faa_enplanements_annual`, `v_faa_cargo_annual` | one row per airport × CY (own workbook preferred, else next year's prior-year column), with `airport_id` |
| `v_taf_enplanements`, `v_taf_operations` | `record_type` historical/forecast, **fiscal_year**, `airport_id`, `total_ops` |
| `v_source_freshness` | loaded vs expected latest period per source |

**Key design decision — airport identity.** Codes are not stable identifiers: Palm Beach is `PBI` in
BTS but `DJT` in FAA CY2025 data (same BTS `AIRPORT_ID` 14027); FAA LIDs differ from IATA codes
(`GPI`=FCA, `IWA`=AZA). Everything is keyed on BTS `airport_id`; any historical code resolves via
`all_codes`/`xref_faa_lid`. Keying on 3-letter codes would have silently dropped or split airports.

## 4. Validation rules

Blocking (vintage rejected): raw checksum mismatch · loader failure · required columns missing ·
row count outside the table's band (T-100 25k–150k/month, on-time 400k–800k/month, …) · nulls in key
columns · negative counts · content period ≠ file period (T-100, on-time) · unknown `aircraft_config`
code · TAF `scenario` not cleanly splitting historical/forecast years · duplicate keys where declared
unique (FAA workbooks, OurAirports, join-critical BTS lookups) · schema incompatible with already
loaded periods.

Warnings (recorded, surfaced, never block): self-loop rows · `passengers > seats` rows · duplicate
codes in history lookups (`L_CARRIER_HISTORY` reuses codes) · TAF duplicate keys · forecast horizon <20y ·
runways referencing unknown airports.

Per-vintage reports: `data/manifest/validation/<source>/<period>/<vintage>.json`; all checks also in
`validation_check`.

## 5. What was ingested (build of 2026-11-04)

| Source | Periods held | Rows | Raw size | Notes |
|---|---|---|---|---|
| BTS T-100 Segment, All Carriers (`FMG`) | 2024-01 … 2026-07 (31 months, contiguous) | 1,453,662 | 55 MB | 208 foreign carriers, 285,861 international rows |
| BTS Reporting Carrier On-Time | 2025-11, 2026-02, 2026-05, 2026-08 (one per season) | 2,305,711 | 113 MB | 515k–612k flights/month |
| BTS lookup tables | snapshot 2026-11-04 (21 lookups) | 49,565 | 2 MB | discovered from form pages |
| FAA CY enplanements (ACAIS) | CY2012–2020, CY2024–2025 | 5,094 | 0.6 MB | CY2021–23 not published as xlsx (CY2025 file carries CY2024) |
| FAA all-cargo landed weight | CY2024–2025 | 155 | <0.1 MB | |
| FAA TAF 2025 (issued Mar 2026) | FY1990–FY2055 | 224k enpl. / 210k ops | 15 MB | 3,319 airports |
| OurAirports | snapshot 2026-11-04 | 86,336 airports / 48,405 runways | 16 MB | |
| Curated constraints | v1 | 31 | <0.1 MB | 11 verified, 20 explicitly unverified |

Totals: 51 vintages, 0 rejected in the final build, 0 uncovered periods. Tests: 46 passed (27 unit, 19 seed-integration; ~2.3 min, offline). Raw archive 202 MB
(largest file 32 MB). Build time ≈ 62 s on a laptop. Fetch log: 51 stored, 1 unchanged, 13 failed
(the failed attempts are the SSL/URL-encoding bugs fixed during development and are kept on
purpose — the log is append-only).

Validation warnings in the final build (non-blocking, all expected): `self_loop_rows` 11,222 rows across
31 months (excluded in `v_t100_segment`), `passengers_le_seats` 234 rows, `L_CARRIER_HISTORY` 208 reused codes.

## 6. Coverage (19 declarative requirements — all pass)

Run: `python -m airport_data coverage`. Highlights:

* T-100: 31 contiguous months; all 12 months of CY2025; zero nulls in core fields.
* FAA hubs (L/M/S, CY2025) present in T-100: **144/144**; all commercial airports ≥10k enplanements: **402/402**.
* FAA LIDs resolving to a BTS `airport_id`: **402/402**; hubs with a TAF forecast: **402/402**.
* Large + medium hubs present in on-time data: **65/65**; operated flights missing taxi/delay: 0%.
* US-origin passengers whose airport resolves to coordinates/state/runways: **99.996%** (126 tiny
  Alaska/bush strips unlocated).
* TAF FY2024 total vs FAA CY2024 boardings: 99% of airports >1M within 5% (median ratio 0.994).
* Freshness: every source `OK` against its expected publication lag.

## 7. Validation-case queries (data availability, not answers)

SQL in [docs/examples/](examples/), actual output in [RESULTS.md](examples/RESULTS.md), asserted by
`tests/test_seed_integration.py`. All are parameterized (region / airport list / thresholds) and resolve
airports through the generic identity layer; `test_q1_generalises_to_another_region` reruns Q1 for the
Mountain division unchanged.

| Case | What the data shows is available |
|---|---|
| Q1 New England expansion inputs | 16 airports ≥10k enplanements in the division with CY2025 boardings + YoY, trailing-12 T-100 pax + YoY + seat factor, TAF FY25→35 growth, runways, curated project rows |
| Q2 LAX vs SNA congestion inputs | on-time delay/taxi/cancel/NAS-share (4 seasons), peak scheduled hour, commercial deps per runway (all carriers), TAF total ops incl. GA (SNA 63% GA vs LAX 2%), cited SNA cap & curfew |
| Q3 ANC long-haul | 12 definition variants: e.g. trailing 12 months ≥3,000 mi = 29.6% all / 4.0% passenger / 51.5% freight; golden test reproduces Phase 0's Jul-2026 23.1% |
| Q4 SFO unmet-demand inputs | 31 monthly seat-factor points (dom/intl), 1,793 route-months (265 routes) for spill-type estimation, delay causes by month, peak scheduled hour vs FAA 2019 modeled rates, TAF domestic/international forecast |

## 8. Phase-1 discoveries that changed the design

1. **Airport codes are not identifiers** → re-keyed on BTS `airport_id` with code history (PBI→DJT inside the T-100 window).
2. **TAF column semantics** → "enplanements" = domestic (`aac+aat+commuter`) **+** international
   (`us_flag+frgn_flag`). A first draft used domestic only (SFO 17.5M instead of 24.8M). Now explicit
   columns plus a cross-source coverage requirement guard against regressions.
3. **TAF `scenario`** = 0 historical / 1 forecast — inferred, enforced as a blocking check.
4. **Publisher format drift**: FAA header spellings vary by year (`Svc Lvl`, `Service Level`, `S/L`,
   `2025 Landed\nWeight`) — CY2014 was correctly *rejected* until an alias was added; BTS lookups are
   Latin-1; lookup URL keys are case-sensitive ROT13 (now discovered from pages, not constructed).
5. **Real duplicate codes** in `L_CARRIER_HISTORY` → uniqueness is a warning there, blocking for join-critical lookups.
6. **FAA capacity profiles are the 2019 edition** (Phase 0 said 2014). A secondary source reports an
   April 2026 FAA change ending side-by-side arrivals at SFO, which would make the 2019 SFO
   "Side-Byes" rates obsolete — recorded as an unverified, material item.

## 9. Limitations, unverified items, manual steps

* **OPSNET (FAA tower ops & delays) not ingested.** The form is JavaScript-driven; a scripted POST
  returned empty. TAF historical operations (annual, all user classes incl. GA) are the substitute.
  Recommendation: one manual export for focus airports, or browser-automation fetcher, if monthly
  total-ops granularity is needed.
* **On-time coverage**: 4 months (one per season), domestic reporting carriers only; no international
  flights; reporting thresholds exclude small carriers/airports. Peak-hour figures from it understate
  international-heavy airports (SFO, LAX, JFK, ANC).
* **No terminal capacity data** (gates, sq ft) exists in any ingested source; only curated project rows.
* **Curated constraints**: 20 of 31 rows are Gemini research not re-verified (marked
  `unverified:*`); LAX capacity rates unverified (FAA PDF 404); SNA cap/curfew verified only via
  search snippets of a City of Newport Beach document. Downstream must quote only `verified:*` rows or
  carry the label through.
* **FAA enplanements CY2021–2023 missing** (FAA posted no xlsx); CY2024 comes from the CY2025 workbook's prior-year column.
* **T-100 lag** ≈ 3–4 months (latest Jul 2026); BTS revises back-months — re-fetching recent months
  periodically will create new vintages (supported, not scheduled).
* **No scheduler.** Refresh is `fetch --all-default` + `build`, run manually; freshness view will flag drift.
* **DB1C / BEA / Census** (Tier 2) not ingested.
* **Seed size**: 202 MB of raw files in git. Acceptable for this project; Git LFS or object storage
  would be the next step if on-time months grow.
* **Gemini headless shell access** was blocked by the session's permission policy, so Gemini was used
  for web-only research; OPSNET investigation was done by Claude.

## 10. Independent code review (Grok) and multi-model log

Grok reviewed the integrity core (rawstore, ingest, build, validation, adapters, derived.sql) and
raised 15 findings; all were checked against the code and **14 fixed** (with regression tests),
1 kept by design:

| Finding | Disposition |
|---|---|
| Snapshot / forecast-release sources would accumulate periods → double counting on 2nd snapshot or next TAF | Fixed: `history_mode = "latest"` (only newest valid period loaded; others `superseded_period`) — `test_latest_history_mode_loads_only_newest_snapshot` |
| FAA annual views could double count an airport whose LID changed (PBI/DJT same CY) | Fixed: one row per `airport_id × cy`, deterministic tie-break |
| `any_value()` non-determinism; on-time forced country `'US'` | Fixed: `arg_max` with fixed ordering; T-100 supplies country |
| OurAirports match could pick a foreign airport / steal via ICAO guess | Fixed: country-constrained IATA arm, guarded ICAO arm |
| A check crash aborted the whole build instead of rejecting the vintage | Fixed — `test_check_crash_rejects_vintage_instead_of_aborting_build` |
| Type sniffing could drift across months | Fixed for T-100/on-time key fields (pinned types); cast failures reject the vintage |
| "Unchanged" didn't re-verify stored bytes (bit rot) | Fixed — `test_identical_download_replaces_bitrotted_copy` |
| Non-atomic `meta.json`; unreadable meta crashed listing | Fixed — atomic replace; unreadable dirs ignored — `test_unreadable_meta_is_ignored` |
| Stale WAL sidecars; concurrent builds | Fixed — sidecars removed, per-pid temp file, lock — `test_concurrent_build_is_refused` |
| On-time row band fixed to 2026 volumes | Fixed — 100k–1M sanity band (CRC remains the primary corruption guard) |
| T-100 `available` returned only the latest month | Fixed — periods derived from the form's year list + latest banner |
| NULL year/month rows passed the period check | Fixed — shared NULL-safe `period_match_check` — `test_rows_with_null_period_fields_are_rejected` |
| Promotion not transactional across a source's tables | Fixed — one transaction per vintage |
| `total_ops` NULL propagation | Fixed — `coalesce` per component |
| Derived SQL failure aborts the build | **Kept by design**: a derived-SQL error is a code bug; failing loudly keeps the previous DB. Removed the unneeded `curated_constraint` dependency. |

Other model use in Phase 1: **Gemini** compiled the curated constraints research (web-only — headless
shell access was denied by the session's permission policy); its rows were spot-checked: SFO capacity
rates confirmed from the FAA PDF (but the cited year was wrong: 2019, not 2014), SNA cap confirmed via
a secondary official document, other "verbatim" quotes could not be confirmed → labelled unverified.

## 11. Recommended next step (Phase 2: analytics layer)

Pure, deterministic functions over the conformed views, each returning
`{value, definition, epistemic_class, sources[], as_of, caveats[]}` from the manifest; unit-tested
against golden values from this DB. Start with the metric primitives the four cases need
(trailing-12 traffic & growth, seat factor, long-haul share by definition, delay/taxi/peak metrics,
TAF growth), then the screening score with visible weights, then the spill estimate as a labelled range.
