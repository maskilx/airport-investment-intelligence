# Phase 2 — Independent Audit, Adversarial Review & Evaluation Log

Reviewer configuration: Grok CLI, `-m grok-4.7 --reasoning-effort xhigh`.
- **Model:** `-m grok-4.7` was requested; the run metadata reports the backend as `grok-4.7-build`.
- **Effort:** the CLI validates the effort level (it rejected `bogus` and listed `xhigh, high, medium, low`), but it does not echo the applied level back. So xhigh was *requested and accepted*. It could not be independently confirmed as applied.
- **Access:** read files, plus one allowed command, `tools/roq.py`. That tool runs read-only SQL: DB opened read-only, external access disabled, one SELECT/WITH statement only. No write permissions.

## 1. Data-foundation audit (16 findings) — disposition

Every finding was reproduced with the auditor's SQL before any change, then re-checked after the fix with the same SQL.

| # | Finding | Status | Fix (verified) |
|---|---|---|---|
| 1 | Two BTS ids for one OurAirports facility (Yuma NYL/YUM, Tuntutuliak) share an FAA LID; LID went to the id without traffic | confirmed | FAA LID owned by the id with T-100 traffic; xref ties broken by traffic. YUM now holds the 85,504 FY25 boardings |
| 2 | Foreign OurAirports `local_code`s used as FAA LIDs (ROS→Rosario AR, REI→Reynosa MX took US grants/NPIAS) | confirmed | FAA LID only for US/territory facilities. ROS = Rush City MN, REI = Redlands CA; foreign LIDs 118 → 0 |
| 3 | BEA combination areas invisible to CBSA totals (Charlottesville 65k vs ~227k; OGG/CHO no CBSA); missing counter stuck at 0 | confirmed | `county_geo` + `county_bea_area` map components → BEA areas; CBSA = Σ distinct BEA areas; a member without data makes the CBSA value NULL and is counted (no silent partials). Charlottesville 227,336; DC metro 6.44M; OGG→Kahului CBSA |
| 4 | ICAO `P/T`+code and FAA-LID arms matched facilities in other states (25 airports) | confirmed | same-state guard on both arms; remaining state differences = 3 legitimate border cases (DCA, CPS, CBE) |
| 5 | Connecticut relievers (BDR, HFD, DXR) on legacy counties → NULL 2024 econ | confirmed | cited overrides added (planning regions) |
| 6 | Activity view counted T-100 self-loops that the segment view drops | confirmed | same rule in both; June 2025 totals now equal |
| 7 | Summing `v_t100_segment.passengers` over all rows double-counts domestic segments | confirmed (semantics) | no change needed. The semantic layer always aggregates departing segments per airport (enplanement side); documented |
| 8 | `zero_operation_rows` could never fail | confirmed | check now `zero == 0` |
| 9 | Documented T-100 grain not unique (needs entity + region) | confirmed | true grain declared as a **blocking** unique key; passes all 31 months |
| 10 | 44 towered airports (e.g. North Perry 0.94M ops) had no airport id | confirmed | NASR-only facilities get stable synthetic ids (900000000 + base-37 of LID); 0 unresolved towers |
| 11 | Passenger totals mix configurations; zero-seat passenger rows unchecked | confirmed | passenger measures = passenger + combi + seaplane; new `passengers_without_seats` warning |
| 12 | Lake Hood / RVR forecasts & boardings had no id | confirmed | covered by #10 |
| 13 | Two FAA workbooks disagree for 2 airport-years; older value preferred | confirmed | latest publication (revised value) now wins |
| 14 | `norm_county` collapses independent city with its county | confirmed, no current impact | the 3 affected airports are verified to be in the county; documented limitation |
| 15 | Build metadata and freshness depend on the clock; `any_value(cbsa_title)` | confirmed | `any_value` → `min`; freshness is clock-relative **by design** (documented); content tables are bit-reproducible (test) |
| 16 | Scottsdale has T-100 passengers but no FAA enplanement row | suspicious | the engine returns NULL (never 0); screen now lists `no_faa_enplanement_record` separately |

The auditor also verified as **correct**:
- FAA CY2025 boardings match the published ACAIS figures exactly;
- the BEA 2024 US population equals the Census Vintage 2024 total exactly (340,110,988);
- the ATADS AUS CY2024 total equals FAA's own report (260,774);
- no view fans out, and every key assumed unique is unique;
- On-Time dates and local hours are consistent;
- ATADS fiscal years roll over in October;
- missing enplanement years are marked missing, not zero;
- BEA suppression flags are preserved;
- grant program NULLs mean "not in that year's layout".

## 2. Adversarial review of the analytics engine
_(filled in below after the review completes)_

## 3. Agent evaluation
_(filled in below after the run completes)_
