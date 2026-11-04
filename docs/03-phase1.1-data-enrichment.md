# Phase 1.1 — Data Foundation Enrichment

Status: **complete, pending review** · Date: 2026-11-04 · Builds on [02-phase1-data-foundation.md](02-phase1-data-foundation.md)

All new data flows through the Phase 1 machinery: vintaged raw archive, adapter + `TableSpec` contract,
blocking/warning validation, fallback to the last valid vintage, transactional promotion, manifest
lineage, offline rebuild. No framework or new infrastructure was added.

## 1. Outcome by priority

| Priority | Result |
|---|---|
| A. On-Time → 12+ consecutive months | **Done**: Sep 2025 – Aug 2026, 12 contiguous months, 7,049,869 flights (matches the published 12-month total). 24 months deferred: +~360 MB of raw zips in git — needs Git LFS/object storage first |
| B. FAA OPSNET | **Integrated** (ATADS airport operations), see §3. OPSNET *delays* deferred |
| C. AIP & NPIAS | **Integrated**: FAA grant detail reports FY2021–2025 (16,828 grants, $39.4B awarded) + NPIAS 2025–2029 Appendix A (3,287 airports, $67.6B planned-need estimate) |
| D. DB1C | Deferred (§4) |
| D. Census / BEA | **Integrated** in a lean form: FAA NASR (airport → county) + Census CBSA delineation (county → metro) + BEA CAINC1 (population & personal income 1969–2024) |
| D. Terminal capacity | **Not ingested**; Gemini research kept as an *unverified worklist* (§4) |
| D. TSA | Rejected (§4) |

## 2. Sources added

| Source id | What | Grain / coverage | Access | History mode |
|---|---|---|---|---|
| `faa_atads_ops` | Tower-counted operations by user class (air carrier, air taxi, GA, military; itinerant/local) | towered airport × month; **2023-10 … 2026-09 (36 months)**, ~527 airports/month | public ATADS form, replayed payload (§3) | accumulate |
| `faa_grants` | Awarded FAA airport grants with amount by funding program (AIP entitlement/discretionary, AIG, COVID relief, FCT, ATRM) + project summary | grant; **FY2021–FY2025** | yearly xlsx | accumulate |
| `faa_npias` | NPIAS airports, role, hub, 5-yr AIP-eligible development **need estimate**; proposed new airports | airport; cycle **2025–2029** | xlsx | latest |
| `faa_nasr_apt` | Official FAA airport master records (county, ownership, use, coordinates) + runways | facility; cycle 2026-10-29; 19,434 facilities / 23,195 runways | NASR 28-day CSV extract | latest |
| `census_cbsa` | OMB/Census county → CBSA / CSA delineation | county; July 2023 | xlsx | latest |
| `bea_cainc1` | County personal income, population, per-capita income | county × year; **1969–2024** | bulk zip (no key) | latest |
| `ref_county_aliases`, `ref_airport_geo_overrides` | Documented county renames (Dade→Miami-Dade, AK divisions) and CT planning-region overrides | small reference CSVs | repo, via raw store | latest |

Also: On-Time extended (8 new months); 4 previously held months re-fetched and correctly logged `unchanged`.

## 3. OPSNET / ATADS — how access was made to work, and its limits

* Phase 1's scripted POST returned empty. Investigation: the public form (`aspm.faa.gov/opsnet/sys/airport.asp`,
  guest access) builds its request **client-side in JavaScript**, including a query string in the `line`
  field, and posts it to `opsnet-server-x.asp`.
* Rather than hand-writing queries, the adapter replays the **exact payload the page's own `checkForm()`
  produces** (captured in a browser with `submit()` intercepted) for a Standard Report, months timeframe,
  all towered facilities, MS Excel format — only the month varies. Template: `sources/atads_payload.json`
  (do not edit `line` by hand). Two request details matter: the `www.aspm.faa.gov` host (session cookie)
  and a `Referer` header.
* Integrity: each month's parsed rows must equal the report's own **Total** row (blocking); component
  identities (itinerant/local/total) are checked NULL-safely; LOCIDs must match `[A-Z0-9]{3,4}`.
* Semantic validation: ATADS FY2024 totals agree with FAA TAF historical operations within 3% at
  **100% of 478 towered airports (median ratio 1.0000)** — TAF history is built from these counts.
* **Not interchangeable with BTS On-Time**: ATADS counts every takeoff/landing by any user at towered
  airports during tower hours; On-Time counts scheduled flights of large reporting carriers. The
  activity view labels the measure (`tower_operations` vs `departures`).
* Risk: the replay depends on the form's payload shape. If FAA changes the page, fetch fails loudly
  (no rows / no total row) and previous vintages keep serving. OPSNET *delay* reports (different form)
  were not integrated.

## 4. Sources investigated but not integrated

| Source | Provides | Assessment | Decision |
|---|---|---|---|
| **DB1C** (40% monthly ticket sample, from Jul 2025) | O&D passengers, fares, itineraries, connections; leakage between nearby airports | High analytical value (true O&D, fare premiums). Not on PREZIP (checked) → TranStats form route; monthly files are large (multi-100 MB raw); excludes ancillary fees; does **not** measure unmet demand | **Defer** to the phase that needs O&D/fares, together with Git LFS/object storage for large raw files |
| **TSA throughput** | National daily screenings; airport-level only in sporadic FOIA PDFs | Airport grain unreliable (irregular PDFs, quarters of lag); national series adds little to airport analysis | **Reject** |
| **Terminal capacity** (gates, sq ft, design MAP) | Master plans, airport sites, bond statements | No structured national source exists. Gemini compiled 98 "high-confidence" facts for 38 airports, but a spot-check found **0/8 quotes verbatim on the cited page and numbers on only 3/8 pages**; most citations were homepages | **Not ingested.** Kept as `research/terminal_facts_unverified.csv` — a worklist to verify per airport when a Phase-2 question needs it |
| **Census PEP / ACS** | County population (PEP), demographics (ACS) | Population already covered by BEA CAINC1 (same Census basis, longer history, plus income). ACS adds detail of weaker relevance | **Defer** (ACS) / not needed (PEP) |
| **BEA GDP (CAGDP)** | County GDP by industry | Useful but secondary to income/population for traffic demand | **Defer** |
| **ATP / AIG award PDFs**, USAspending | Terminal-program selections, allocations; award lifecycle dates | PDF tables or name-matched recipients; AIG dollars already appear in the grant reports | **Defer** |
| **AIP grants FY ≤ 2020** | Older per-project layout | Different schema (project lines, no funding-program totals) | **Defer** (separate adapter if needed) |

## 5. Data dictionary (new objects)

| Object | Key columns / meaning |
|---|---|
| `atads_airport_ops` | `locid, year, month, itn_air_carrier, itn_air_taxi, itn_general_aviation, itn_military, itn_total, local_civil, local_military, local_total, total_operations` |
| `v_atads_airport_ops` | + `period_month`, **`fiscal_year`** (Oct–Sep), `airport_id`, `bts_code` |
| `faa_grant` / `v_faa_grant` | `fiscal_year` (federal FY of award), `locid, sponsor, grant_number, award_date`, program amounts (`entitlement, discretionary, discretionary_noise, discretionary_map, supp_discretionary, cares, econ_recover, aig, fct, atrm`; NULL = column not in that year's layout), `total_amount` (= sum of programs, checked per row), `project_summary`, `airport_id` |
| `npias_airport` | `npias_cycle, locid, ownership, svc_lvl, hub, role, enplaned` (+`enplaned_basis`, e.g. CY23/FY25), `based_aircraft`, `development_estimate` (USD, 5-yr **need estimate**) |
| `npias_new_airport` | proposed new/replacement airports with cost estimate |
| `v_airport_investment_records` | **One status domain across record types**: `record_type` ∈ {faa_grant, npias_development_estimate, npias_new_airport_estimate, curated_project}; `status` ∈ {awarded, announced (no award date → preliminary), planned_need_estimate, proposed, planned, under_construction, completed, in_effect}. **Never sum `amount_usd` across record types.** |
| `nasr_airport`, `nasr_runway` | FAA master records (APT_BASE / APT_RWY), all columns, snake_case |
| `cbsa_county` | `county_fips → cbsa_code, cbsa_title, metro_micro, csa_code, central_outlying` |
| `bea_county_income` | long: `geofips, line_code` (1 income $000, 2 population, 3 per-capita $), `year, value, value_flag` (suppression) |
| `dim_county` | BEA county list (incl. Virginia combination areas, CT planning regions) |
| `xref_airport_county` | `airport_id → county_fips → cbsa`, with `match_rule` ∈ {nasr_county_name, reference_alias, reference_airport_override, bea_combination_area} |
| `v_county_econ_annual`, `v_cbsa_econ_annual` | population, personal income (USD), per-capita; CBSA = sum of member counties (per-capita recomputed) |
| `v_airport_area_econ` | airport's **home** county & CBSA economy by year — an administrative proxy, not a measured catchment |
| `v_source_period_status` | every expected period per monthly/annual source: `loaded / missing / not_yet_expected` (fiscal-year sources use Oct–Sep + lag) |
| `v_airport_month_activity` | airport × month × source: `activity` = 0 when the month is loaded and the airport had none; **NULL when the source month is not held**; `activity_measure` labels departures vs tower operations; ATADS rows only for towered airports |

## 6. Coverage (32 declarative requirements — all pass)

New requirements added in 1.1 (`config/coverage.toml`): on-time 12 contiguous months; reporting-carrier
set stable month to month (12–14 carriers, flight ratio 0.93–1.19); no missing expected periods
(documented FAA CY2021–24 workbook gap listed explicitly); ATADS 24+ contiguous months (36 held);
65/65 large+medium hubs in ATADS; ATADS ↔ TAF FY2024 agreement; grant dollars resolving to airports
(92.1%; unresolved = GA airports never in BTS traffic, statewide grants); 0 hub grants orphaned; grant
numbers unique across FY files; NPIAS covers 401/402 commercial airports; commercial airports with
county **388/393** (excl. territories, which BEA does not cover) and CBSA 354; BEA series 1969–2024,
3,149 counties; metro share of US population 85.4% (sanity check of the aggregation).

## 7. Integrity issues found and handled

| Issue | Handling |
|---|---|
| ATADS form is JS-generated; naive POST returned empty | Replay of the page's own payload; host + Referer; total-row reconciliation |
| FAA grant layouts drift (`SUM(DISC_NOISE_AMT)` headers, FY2022 formula footer row, blank rows) | Aliases; rows kept only with a valid grant number; per-row total = sum-of-programs check (passes all 5 years) |
| 4 FY2022 grants without award date | Status `announced` (FAA: amounts preliminary), never `awarded` |
| COVID-era column `CARES` also carries CRRSA/ARPA dollars in FY2021–22 | Documented as the publisher's combined COVID-relief column |
| NASR `SITE_NO` shared by two facilities (TX airport + heliport) | Key changed to `ARPT_ID` (blocking); duplicate recorded as warning |
| NASR keeps old county names (DADE, Alaska divisions); Virginia independent cities | Normaliser + cited alias table |
| **Connecticut replaced counties with planning regions** (NASR legacy counties; CBSA 2023 regions; BEA both, regions only from 2024) | Cited airport-level overrides (BDL, HVN, GON); CT metro growth before 2024 is NULL (unknown), not zero |
| NPIAS `LocID` header → `loc_id`; first build rejected the vintage | Alias; validation blocked it rather than loading partial data |
| Grok review (12 findings): ATADS missing months could read as zero; on-time "departures" counted cancelled flights; fiscal-year sources judged on calendar years; status vocabulary inconsistent; curated rows joined on FAA LID instead of IATA; NULL-unsafe ATADS identities | Fixed with tests. Two claims were disproven by data (ATADS rows "dropped"; NPIAS new-airports sheet "fails") |
| Gemini terminal facts: unverifiable quotes | Not ingested (see §4) |

## 8. Size & ingestion impact

| | Phase 1 | Phase 1.1 |
|---|---|---|
| Sources | 9 | 17 |
| Vintages loaded | 51 | 106 |
| Raw archive (committed) | 202 MB | **458 MB** (on-time 345 MB) |
| DuckDB file (rebuildable, git-ignored) | 329 MB | 1.0 GB |
| Full offline build | ~62 s | ~100 s |
| Tests | 46 | see completion report |

## 9. Remaining gaps & limitations

* On-Time: 12 months only (24 needs large-file storage); domestic reporting carriers only.
* ATADS: towered airports and tower hours only; OPSNET delays not ingested; payload-replay dependency.
* Grants: FY2021–2025 only; awarded ≠ spent/completed; no lifecycle status in source; `atrm` program label unverified.
* NPIAS: one cycle (2025–29); estimates are sponsor-reported needs, not commitments.
* Geography: 5 commercial airports without county (territories, Klawock AK); CBSA is a proxy for market area; CT history break at 2024.
* Terminal capacity: still no verified, structured data.
* DB1C fares/O&D: deferred.

## 10. Recommendation for Phase 2

Proceed to the Analytics Engine. The foundation now supports, with documented semantics: traffic &
capacity (T-100), domestic airside performance (On-Time, 12 months), all-user tower activity (ATADS),
forecasts (TAF), investment context (grants awarded vs NPIAS need vs curated projects), and regional
economy (county/CBSA population & income). Before any analytics that depends on terminal capacity or
fares, run a targeted verification pass on the terminal worklist for the airports in scope, and plan
Git LFS before DB1C or 24-month On-Time.
