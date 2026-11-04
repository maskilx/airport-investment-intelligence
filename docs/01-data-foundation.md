# Phase 0 — Data Foundation: Findings & Proposed Architecture

Status: **For review (rev 2, after Grok's independent review)** · Date: 2026-11-04 · Owner: Claude (tech lead)

Tags: **[verified]** = Claude fetched it by script from the source on 2026-11-04. **[review]** = raised by Grok's review and checked by Claude. **[unverified]** = documented claim we have not tested.

---

## 1. Bottom line

- **Free federal data (BTS, FAA) plus OurAirports covers all four example questions.** The MVP needs no commercial feed.
- **Two concepts the investment questions hinge on are never directly observed: terminal capacity and unmet demand.** The system will publish *indicators* and *bounded estimates*, labeled as such. It will never present them as measurements.
- **Forward seat schedules (OAG, Cirium, FlightAware) are the main data we lack.** They are paid, and their licenses restrict B2B use and derived databases. We note them as the production upgrade.
- **Architecture: local-first.** Versioned raw files feed validated DuckDB tables, which feed deterministic, tested analytics functions. The LLM only calls tools. Every number it shows comes from a tool result that carries its definition, source and as-of date.

## 2. Source inventory

### Tier 1 — MVP core

| Source | Gives us | Access (tested) | Latest (2026-11-04) | Notes / traps |
|---|---|---|---|---|
| **BTS T-100 Segment, All Carriers** (TranStats code `FMG`) | Monthly carrier × O×D × aircraft: departures sched/performed, seats, pax, freight, distance, `CLASS`, `AIRCRAFT_CONFIG`, countries | No API. ASP.NET form POST with VIEWSTATE replay **[verified]**: ~10 s/month, ~48k rows/month | **Jul 2026** | Includes foreign carriers and international flights (`FIM` is US-carrier domestic only, so don't use it). `CLASS` F = scheduled passenger/cargo incl. mixed, G = scheduled all-cargo, L/P = non-scheduled **[review]**. Split passenger vs cargo with `AIRCRAFT_CONFIG`, not `CLASS`. Passengers are *on-board segment* passengers, including through passengers. BTS revises back months, so we store vintages. |
| **BTS Reporting Carrier On-Time** | Per flight: sched/actual times, delays, taxi-out/in, delay causes, cancellations | Static monthly zips at `transtats.bts.gov/PREZIP/` **[verified]** | **Aug 2026** | Coverage: carriers with ≥0.5% of domestic revenue, and only at airports with ≥0.5% of enplanements in the lower 48. Other domestic reporting is voluntary. No international flights, and Alaska/Hawaii may be thin **[review]**. Delay-cause minutes exist only for late flights. Row count: see §5. |
| **FAA CY Enplanements (ACAIS)** | Official annual boardings, hub class, YoY | xlsx on faa.gov **[verified]**: `Locid, Hub, CY 25 Enplanements, CY 24 Enplanements, % Change` | **CY2025** | Revenue enplanements, defined differently from T-100. ANC also counts transit passengers on international technical stops **[review]**. |
| **FAA TAF 2025** | Enplanement and operations forecasts per airport, FY2025–FY2055 | Full download `taf.faa.gov/Downloads/APO100_TAF_Final_2025.zip` (Enplanements, Operations, BasedAircraft, Tracon xlsx, dated 2026-03-20) **[verified]**; no form scraping needed | **issued Mar 2026** | **US fiscal years (Oct–Sep).** Convert before comparing with calendar-year data **[review, confirmed by file name]**. The forecast is unconstrained by capacity, but its baseline is built on constrained history **[review, unverified for 2025]**. |
| **OurAirports** `airports.csv`, `runways.csv` | Coordinates, IATA/ICAO, runways (length, surface) | Static CSV, nightly **[verified]** | nightly | Public domain, no accuracy warranty. |
| **FAA OPSNET** (public part) | Monthly tower operations (air carrier, air taxi, GA, military) and reportable delays | Web form on aspm.faa.gov. Grok says final data is public around the 20th of the following month **[review]**; scripted access **[unverified]** | — | The congestion denominator that on-time data lacks (all operations, not just reporting carriers). If scripting fails, we take a one-off manual extract for the focus airports. |
| **Curated constraints and projects table** (hand-built) | Facts no dataset holds: SNA's passenger cap and curfew; SFO's closely spaced parallel runways; 2014 FAA capacity-profile *modeled* rates (Core 30); NPIAS/terminal programs for focus airports | Manual. Each row carries URL, retrieval date, effective date and review date | static | Answers quote a row with its citation, or say nothing. A stale row gets flagged. |

### Tier 2 — enrichment (after the MVP works)
1. **DB1C** (successor to DB1B since **July 2025**: a 40% monthly ticket sample instead of 10% quarterly **[verified via BTS/libanswers]**). Gives fares and true O&D demand, useful for fare premiums (a sign of constrained supply) and leakage to nearby airports. *My draft had this wrong: DB1B isn't lagging, it was replaced.*
2. **BEA/Census APIs**: metro population and income growth (free key).
3. **TSA checkpoint throughput**: near-real-time trend checks only **[unverified airport-level format]**.

### Rejected
- **FAA ASPM efficiency, taxi and flight-level data**: login only **[verified]**.
- **OpenSky, ADS-B Exchange**: aircraft positions, not schedules. Commercial use barred.
- **OAG, Cirium**: the right data, but procurement takes weeks and licensing restricts derived databases.
- **FlightAware AeroAPI**: B2B use needs Premium ($1k/mo minimum).
- **AviationStack, AeroDataBox**: no verified seat counts, and cache rules are short.
- **ACI, A4A**: paid, internal-use only, or restate BTS data.

Details: [research/commercial_sources.md](../research/commercial_sources.md) (Grok, with cited URLs). Prices weren't re-verified, because licensing alone decides these.

## 3. Coverage of the example questions

| Question | Inputs | What we can honestly return |
|---|---|---|
| **New England terminal-expansion candidates** | FAA CY enplanements + hub class, TAF FY growth, T-100 rolling 12 months, NPIAS/curated projects | Ranked indicators: scale, recent growth, forecast growth, rolling 12-month seat factor, existing planned projects. **Annual or rolling-12 data only**, so seasonal July peaks don't rank Cape and Maine airports first. Size is shown next to any rate. No terminal capacity data exists, so we say so. |
| **LAX vs SNA congestion** | On-time (domestic airside delay, taxi-out, peak-hour schedule), OPSNET operations and delays, runways, constraints table | Three separate lines, never blended: (1) domestic airside delay metrics, (2) total operations per runway and OPSNET delays, (3) the regulatory constraint (SNA cap/curfew, cited). We state that LAX international flights fall outside the on-time file. |
| **% long-haul flights out of ANC** | T-100 departures performed × distance × `AIRCRAFT_CONFIG` | A **definition-explicit** table: passenger / cargo / all at 2,000, 3,000 and 3,500 mi. July 2026 test at ≥3,000 mi gave 23.1% all, 4.2% passenger (seats > 0), 53.7% cargo. To be recomputed using `AIRCRAFT_CONFIG` and a rolling 12 months. The agent states the definition it used. |
| **SFO unmet demand and drivers** | T-100 seat factor and seats, TAF, on-time delay causes, OPSNET, constraints | **Unmet demand is not identified from public data.** We return: (a) observed pressure indicators (seat factor, peak scheduled departures, weather/NAS delay share); (b) a *lower-bound spill estimate on existing flights* from a standard spill model, as a range across assumed demand variability, stating that it excludes demand that never became a scheduled flight; (c) drivers as cited facts (runway spacing, IFR rates) or labeled hypotheses. |

## 4. Architecture

```
 fetchers (one per source): probe "latest available" → download → CRC + sha256
        ▼
 data/raw/{source}/{period}/{fetched_at}/file     (vintaged; newest valid vintage serves)
        ▼
 validate: blocking = structural  |  warning = plausibility
        ▼ pass
 build new DuckDB file → swap on success (old file kept) + ingest_manifest table
        ▼
 analytics/  pure deterministic functions → {value, definition, sources[], as_of, caveats[]}
        ▼
 agent tools (Claude tool use) → chat UI
```

Decisions:
- **DuckDB, one file, no server.** On-time data is stored as airport × month × hour aggregates, not raw flights.
- **Downloads, not APIs.** No Tier 1 source has a usable API. "External retrieval" happens at refresh time (each source's latest-available marker is probed). The chat path is offline and reproducible.
- **Seed extracts committed to the repo.** The demo can't break if BTS is slow or its form changes. Fetchers regenerate the seeds.
- **Manifest** (`source, period, vintage, url, sha256, rows, schema_hash, status`) feeds the as-of and staleness labels in every answer.
- **Revisions:** BTS revises earlier months (the 2026-10-09 release updated April 2026) **[review]**. Raw files are vintaged, not overwritten.

## 5. Validation (kept deliberately small)
**Blocking** (structural):
- Zip CRC passes.
- Header matches the expected columns.
- Row count is inside a sane band.

On the zip CRC: testing hit a silently truncated BTS download, and a `curl -C -` resume grafted one file onto another. Only the CRC check caught it.

**On-time row count, corrected.** Grok flagged my "~225k rows/month" as too low (published counts are ~608k for Aug 2026). It was right. The figure came from the corrupted file above, which shows exactly why that check must block. A fresh download passed the CRC check and contains **608,389 flights [verified]**, which matches the published figure exactly. The blocking row-count band for on-time data is set at 450k–750k flights/month.

**Warnings only:**
- `passengers > seats`.
- Distance vs great-circle beyond 15 mi absolute. *A percentage tolerance would reject short New England hops.*
- Self-loop rows, which are excluded. July 2026 had 445.
- T-100 vs FAA enplanements. **This is diagnostic only.** The definitions differ (segment passengers include through passengers; FAA counts revenue enplanements and ANC transit passengers), so a gap is expected, not an error.

**Naming discipline:** an airport-level `passengers/seats` ratio is a *seat factor*. Load factor means RPM/ASM, which requires weighting by distance.

## 6. Analytics, by epistemic class
| Metric | Class |
|---|---|
| Departures, seats, pax, seat factor, route mix, long-haul share, YoY | Observed / calculated |
| Delay rate, taxi-out, delay-cause share (*of late minutes*), peak-hour scheduled departures, ops per runway | Observed / calculated |
| TAF growth (FY) | Forecast, FAA, cited |
| Spill on existing flights | Estimate, lower bound, range shown |
| Opportunity score | Calculated composite (see below) |
| Causal drivers | Cited fact or labeled hypothesis |

**On scoring (where I diverge from Grok):** Grok recommended dropping the composite score entirely. The assignment explicitly requires *deterministic scoring logic*, so we keep one. Its guardrails:
- Annual and rolling-12 inputs only.
- Percentile-normalized against a peer set (same hub class).
- Weights are fixed, visible, and documented in the architecture doc.
- Every sub-score is returned with the total.
- The score is presented as "a screening rank, not a valuation."

## 7. Risks
1. **The BTS form scraper is fragile.** Mitigation: commit seed extracts, run a smoke test.
2. **Lag.** T-100 trails by about 4 months, CY enplanements by about 10. Every answer shows its as-of date.
3. **Capacity ground truth is weak.** ASPM is login-only, and the 2014 profiles are modeled rates. All capacity figures are labeled proxies.
4. **On-time coverage bias.** No international flights, plus the 0.5% airport rule. This biases ANC, SFO, LAX and small New England airports.
5. **Estimates repeated as facts.** Mitigation: the tool output schema forces `definition` + `class` + `caveats`, and the system prompt forbids numbers that didn't come from a tool.
6. **Stale curated constraints.** Each row has review dates; stale rows are flagged in answers.

## 8. Proposed next phase (Phase 1: ingestion, scoped to the deadline)
1. Repo skeleton: Python 3.12, DuckDB, pytest (no other frameworks).
2. Fetchers + manifest + blocking validation for:
   - T-100 `FMG`, 12 months (national; needed for peer-set scoring)
   - On-time, 3 months, aggregated to airport × hour
   - FAA CY2024–25 enplanements
   - TAF 2025 zip
   - OurAirports
3. OPSNET: test script access. If it fails, do a manual extract for LAX, SNA, SFO, BOS and ANC.
4. Curated constraints and projects CSV: ~15 cited rows.
5. Tests:
   - validators reject a truncated zip
   - golden ANC long-haul figures
   - CY↔FY mapping
   - idempotent rebuild
6. **Exit criteria:** one command builds the DB from seeds; the manifest is complete; the raw inputs for all four questions can be queried in SQL; the tests pass.

## Appendix — review log
| Grok finding | Decision |
|---|---|
| DB1B replaced by DB1C | Accepted (verified) |
| TAF: zip download, fiscal years | Accepted (verified) |
| On-time ~225k rows too low | Accepted. The cause was a corrupt file; recount = 608,389 (verified) |
| On-time coverage rule; `CLASS` semantics | Accepted (doc-level) |
| T-100 vs FAA cross-check invalid as a gate | Accepted → diagnostic only |
| Spill model ≠ unmet demand | Partly accepted → kept as a labeled lower bound on existing flights |
| Drop composite score | Rejected (assignment requires scoring) → guardrails added |
| Over-engineering | Partly accepted: no quarantine machinery, seeds committed, on-time cut to 3 months. National T-100 kept |
| Add OPSNET, NPIAS | Accepted (OPSNET Tier 1 pending an access test; NPIAS in the curated table) |
| Raw "immutable" vs BTS revisions | Accepted → vintaged storage |
