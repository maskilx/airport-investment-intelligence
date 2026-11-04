# Phase 2 — Analytics Engine: Research, Architecture & Plan

Status: **proposal for review (no implementation yet)** · Date: 2026-11-04 · Owner: Claude (tech lead)
Inputs: assignment brief · Phase 0–1.1 docs · probes against the built DB (§2) · methodology research (Gemini, cited, spot-checked) · independent critique (Grok, §11)

Labels used below: **[measured]** = I queried it in our DB today · **[cited]** = from an external methodology source (marked *to verify* where I have not opened the primary document) · **[proposal]** = my recommendation.

---

## 1. Assignment analysis

**The core ask.** "Identify airports where renovations will be most profitable based on increased flight and passenger capacity." Everything else (the four questions, the chat UI) serves that. Three implications:

1. **The answer is a ranking with reasons, not a lookup.** The evaluator will probe *why A ranks above B* and *what would change the ranking*. Deterministic scoring with decomposable contributions is the centrepiece, not a garnish.
2. **"Profitable" is not directly observable from traffic data.** A defensible system must say what it actually measures (expansion *pressure* and *opportunity*), what it proxies (revenue per passenger), and what it cannot see (costs, debt, airline agreements, construction risk). Over-claiming here is the most likely way to lose the evaluator's trust.
3. **The example questions span four answer types**, which the engine must support generically:
   | Example | Answer type | Hard part |
   |---|---|---|
   | New England terminal candidates | *rank within a set* | scoring, region resolution, missing terminal data |
   | LA vs Santa Ana congestion | *compare entities* | ambiguity ("LA" = LAX or the LA basin?), source coverage differences |
   | % long-haul out of ANC | *single metric* | definition choice (threshold, passenger vs cargo) |
   | SFO unmet demand & why | *estimate + causal explanation* | unmeasurable quantity; separating evidence from hypothesis |

**What will impress a technical interviewer** (my read):
- Numbers that **reproduce** and carry their **lineage** (source, period, vintage).
- Visible **epistemics**: the system distinguishes observed / calculated / estimated / forecast / hypothesis, and says "cannot establish" when it can't.
- **Definition-awareness**: asks or states which definition of "long-haul" and "LA" it used.
- A scoring model whose weights are **explicit, configurable, sensitivity-tested**, with rank *intervals* rather than false precision.
- Clear **LLM/deterministic boundary**, with a mechanism that *enforces* it (not just a prompt).
- Generality demonstrated live: the same machinery answers a question nobody pre-scripted.

**What would make answers misleading** (and must be designed against): comparing delay rates across airports with different On-Time coverage; treating seat factor as proof of unmet demand; summing NPIAS estimates with awarded grants; reading missing months as zero; ranking by a score that silently imputes missing inputs; presenting TAF (an FAA forecast) as an observation; precision theatre (score 73.4 vs 72.9 as meaningful).

## 2. Current foundation assessment

### 2.1 What the probes showed [measured]

| Finding | Evidence | Consequence |
|---|---|---|
| **T-100 enplaned passengers are a reliable demand base** | T-100 CY2025 origin passengers / FAA ACAIS CY2025 = 0.994–1.010 at 11 test airports | Use T-100 as the monthly passenger series; ACAIS as annual anchor |
| **T-100 ops ≈ ATADS commercial ops** at big hubs | 2×departures / ATADS (air carrier + air taxi) = 0.93–0.98 at ATL/LAX/JFK/BOS/SFO; 0.70–0.80 at HNL/ANC/SNA/MHT (air taxi, cargo, GA-heavy) | Use ATADS for *airfield* activity, T-100 for *airline capacity*; never mix in one ratio |
| **On-Time covers only part of traffic, unevenly** | operated reporting-carrier deps / T-100 passenger deps: SNA 0.88, ATL 0.80, SFO 0.78, LAX 0.75, ANC 0.50, JFK 0.48 | Delay/taxi/peak metrics must carry a **coverage ratio** and be flagged when <0.7; peak-hour counts are *lower bounds* |
| **Seat factor is a weak discriminator** | T12 seat factor, large hubs: p10 0.765, median 0.803, p90 0.821; SFO 0.821 (not exceptional) | Low weight in scoring; unmet demand must use route-month distributions, not airport averages |
| **Peak-hour schedule vs modeled capacity is a strong constraint signal where capacity is known** | SFO scheduled ops (reporting carriers only): p95 hour 66, max 82; FAA 2019 profile: IFR 71–74, VFR 104–107 ops/h | Most defensible SFO "why" evidence. But capacity rates are verified only for SFO today |
| **Investment-need proxies vary widely** | NPIAS need per enplanement: JFK $8 → ANC $117; TAF FY25→35 growth: BDL 16% → SFO 32% | Usable as dimensions after normalization; NPIAS is sponsor-declared need, not a measured gap |

### 2.2 What we can and cannot answer

| Capability | Status | Basis |
|---|---|---|
| Traffic, seats, departures, growth, route mix, carrier mix, long-haul share by definition | ✅ reliable | T-100, 31 months |
| Domestic airside performance (delay rates, delay minutes by cause, taxi-out, cancellations, schedule peaking) | ✅ with coverage caveat | On-Time, 12 months |
| All-user airfield activity (incl. GA, military), utilization vs a capacity proxy | ✅ activity; ⚠️ capacity = proxy | ATADS 36 months; runway inventory (NASR); FAA capacity rates only where curated |
| Forecast growth | ✅ as **forecast** | TAF 2025 (fiscal years) |
| Investment context (awarded grants, declared need, documented projects) | ✅ with status semantics | FAA grants, NPIAS, curated |
| Regional economy (home-CBSA population, income, growth) | ✅ as proxy for market area | BEA + CBSA + NASR county |
| **Terminal capacity** (gates, sq ft, design MAP) | ❌ no verified data | worklist only |
| **Fares, O&D demand, leakage, yield** | ❌ | DB1C deferred |
| **Airport financials** (revenue per enplanement, debt, CPE) | ❌ not ingested, **but obtainable** | FAA CATS (Form 127), see §9 decision point |
| Latent demand of non-flyers, airline intentions, construction cost | ❌ out of scope | — |

### 2.3 Data-model risks the engine must guard against [measured/proposal]
- **Grain mismatch / double counting**: T-100 rows are carrier×segment×aircraft; airport totals must aggregate *departing* segments only (origin side) for enplanements, both sides for operations. Through passengers are counted at each enplanement, which matches FAA's definition, so it is correct for airport throughput but wrong for O&D.
- **Denominators**: seat factor = Σpax/Σseats over passenger-configured flights with seats>0 (cargo excluded). Load factor (RPM/ASM) is a different metric; name both correctly.
- **Time alignment**: T-100 ends Jul 2026, On-Time Aug 2026, ATADS Sep 2026, TAF in fiscal years, ACAIS and BEA in calendar years. Every cross-source metric needs an explicit common window or must report per-source windows.
- **Peer-group fairness**: normalization must happen within comparable airports (hub class), or small airports' volatile ratios dominate rankings.
- **Identity**: always key on `airport_id` (PBI→DJT happens inside our window).

## 3. Recommended architecture [proposal]

### 3.1 Shape: a deterministic analytics library with a typed tool surface

```
                ┌──────────────────── airport_analytics (new package, no LLM inside) ───────────────────┐
 question  ──►  │ tools.py        5 coarse capabilities with JSON-schema'd params (framework-agnostic)       │
 (agent,        │   └─► analyses/   compose primitives: profile, compare, rank, long_haul, congestion,      │
  CLI, tests)   │                   demand_pressure, investment_context, rank + scenarios, explain_rank    │
                │        └─► metrics/  catalog of MetricSpec (id, formula, unit, class, grain, caveats)      │
                │             └─► core/  resolver (entities) · windows (time & coverage) · query (DuckDB)   │
                │                        · evidence (Finding, Evidence, Caveat, Quality)                    │
                └───────────────────────────── reads ▼ only ─────────────────────────────────────────────────┘
                                 airport_data DuckDB (conformed views + ingest_manifest)
```

**Why a library + tool surface rather than alternatives**
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| LLM writes SQL (text-to-SQL) | flexible | non-deterministic, hard to validate, denominator mistakes invisible, lineage lost | ❌ (maybe later as a guarded "exploratory" tool with explicit `class=exploratory`) |
| Many fine-grained metric tools (one per metric) | simple | 60+ tools overwhelm tool selection; composition pushed to the LLM | ❌ |
| **Coarse capability tools over a metric catalog** | small tool surface, deterministic composition, each result self-describing | needs upfront design | ✅ |
| Microservice / API server now | deployable | infra without need | ❌ now; FastAPI wrapper is trivial later because tools are plain functions |

### 3.2 Core components

1. **Evidence model (`core/evidence.py`)**: every analytical output is a `Finding`:
   ```
   Finding(id, subject{airport_id, code}, metric_id, value, unit, window{start,end,basis},
           epistemic_class ∈ {observed, calculated, estimated, forecast, hypothesis, not_established},
           definition (human text + formula ref), method, inputs[Finding ids],
           sources[{source_id, periods, vintage_ids}], as_of, coverage{ratio, note},
           caveats[code+text], coverage{ratio, scope})      # caveat codes, no letter grades
   ```
   `not_established` is a first-class outcome ("cannot be determined from available evidence because …"). Lineage is pulled from `ingest_manifest` automatically, never written by hand.
2. **Entity resolver (`core/resolve.py`)**: names, codes (incl. historical), cities, CBSA/CSA ("LA area"), states, Census divisions/regions → `airport_id`s, returning **candidates + ambiguity** instead of guessing ("LA" → {LAX} or {LAX, BUR, LGB, ONT, SNA} → the agent asks or states the assumption).
3. **Windows & coverage (`core/windows.py`)**: named windows (`T12`, `CY2025`, `FY2025`, `latest_common_T12`) resolved per source against `v_source_period_status`. A request outside coverage gets a typed `OutOfCoverage` error with the available range, never a silent shrink.
4. **Metric catalog (`metrics/`)**: declarative `MetricSpec` (id, name, unit, epistemic class, grain, SQL template over conformed views, required sources, applicability rules such as "towered airports only", caveat rules such as "on-time coverage < 0.7 → caveat ONTIME_LOW_COVERAGE", comparability group). Metrics are computed **vectorized for a set of airports** in one query. The catalog is itself exposed (`list_metrics`), so the agent can discover rather than hallucinate capabilities.
5. **Analyses (`analyses/`)**: composable functions returning `AnalysisResult{findings[], tables[], narrative_facts[], open_questions[]}`, where `narrative_facts` are machine-checkable statements ("SFO p95 scheduled hour (66) < IFR modeled capacity upper bound (74)") the agent may paraphrase.
6. **Scoring (`scoring/`)**: config-driven model (TOML): anchored scales, weights, gate, flags, scenarios; outputs score, additive contributions, flags, not-scored list, scenario rank table (§5).
7. **Tool surface (`tools.py`)**: `ToolSpec(name, description, json_schema, handler)` registry; handlers validate inputs (enum metrics, bounded airport sets, known windows) and return JSON-serializable results. Usable from Claude tool-use, MCP, FastAPI or a CLI without change.

Dependencies: none new (DuckDB + stdlib dataclasses; JSON schema hand-written or generated from dataclasses).

## 4. Metric methodology [proposal; formulas are deterministic SQL over existing views]

Conventions: airport = `airport_id`; T12 = trailing 12 complete months of the source; growth = (T12 / prior T12) − 1; all ratios computed as Σnumerator/Σdenominator (never mean of ratios) unless stated.

| Metric | Definition (numerator / denominator) | Source · window | Class | Key caveats |
|---|---|---|---|---|
| `enplanements` | Σ passengers on departing segments | T-100 · T12/CY | observed | includes connecting pax (FAA-consistent) |
| `realized_growth` | T-100 T12 / prior T12 − 1 (airport identity spliced by `airport_id` first) | T-100 | calculated | separate id `acais_cy_growth` for CY25/CY24 |
| `incremental_enplanements` | TAF total enplanements FY2035 − FY2025 | TAF | **forecast** | unconstrained; may assume projects |
| `seats`, `seat_factor` | Σpax / Σseats, passenger+combi configs, seats>0 | T-100 · T12 | calculated | compressed range; not "demand" |
| `segment_load_factor_dw` | Σ(pax·dist) / Σ(seats·dist) on departing segments (not system RPM/ASM) | T-100 | calculated | distance-weighted |
| `departures`, `seats_per_departure` | Σdepartures performed; Σseats/Σdeps (gauge) | T-100 | observed/calc | gauge growth = capacity without slots |
| `route_count`, `new_routes`, `lost_routes` | distinct dests with ≥ N deps in the T12 total (not per month: avoids seasonal churn) | T-100 | calculated | threshold N stated |
| `top_carrier_share`, `carrier_hhi` | seat share of the largest **operating** carrier (T-100 has no marketing carrier); HHI | T-100 seats · T12 | calculated | regional affiliates split the hub tenant → understates concentration; used as a flag |
| `intl_share` | intl seats / seats | T-100 | calculated | — |
| `long_haul_share(d, scope, weight)` | share of departures **and** of passengers (or freight tonnage) on segments ≥ d statute miles; scope ∈ passenger/freight/all | T-100 · T12 | calculated | **definition is a parameter**; default answer shows passenger- and freight-weighted rows side by side |
| `ops_total`, `ops_by_user`, `ops_growth` | ATADS tower ops | ATADS · T12/FY | observed | towered airports, tower hours |
| `peak_hour_ops_p95`, `peak_hour_ops_max` | 95th pct / max of hourly scheduled arr+dep, reporting carriers | On-Time · 12m | observed (lower bound) | coverage ratio attached |
| `peak_vs_capacity` | p95 hour / modeled hourly capacity (VMC, IMC) | On-Time + curated | calculated | only where a **verified** capacity rate exists |
| `dep_delay15_rate`, `arr_delay15_rate` | flights ≥15 min late / operated flights | On-Time | calculated | coverage; domestic only |
| `nas_delay_min_per_arr` | Σ NAS delay minutes / operated arrivals in the same file | On-Time | calculated | per arrival, **not** share of late minutes; NAS = airspace/system, not terminal |
| `weather_delay_min_per_op`, `cancel_rate` | analogous | On-Time | calculated | — |
| `taxi_out_p50` | median taxi-out minutes | On-Time | calculated | airport geometry and fleet mix dominate; context only, never ranked |
| `taf_growth(h)` | TAF total enplanements FY(base+h)/FY(base) − 1; also ops | TAF · FY | **forecast** | FAA unconstrained forecast |
| `cbsa_pop_growth`, `cbsa_income_growth`, `cbsa_pc_income` | home-CBSA levels and 10-yr / 5-yr growth | BEA · CY | observed/calc | CBSA ≠ catchment; CT break 2024; multi-airport CBSAs shared |
| `grants_awarded_5y`, `terminal_grants_5y` | Σ awarded (FY21–25); keyword-tagged terminal subset | FAA grants | observed / calc (tag = heuristic) | awarded ≠ spent |
| `npias_need`, `npias_need_per_enp` | 5-yr AIP-eligible need estimate; ÷ CY enplanements | NPIAS | **estimated (sponsor)** | not funding |

Excluded on purpose (weak or unsupported): gates/sq-ft terminal utilization (no verified supply data); fare premiums (no fares); ASV-by-runway-count utilization (AC 150/5060-5 needs runway-use configuration and mix index, not a count); taxi-time spread as "excess" (no unimpeded baseline); TPHP and CSA market share (deferred until formulas are checked against primary documents); "delay share" headlines; any index mixing ATADS and On-Time units.

**Comparisons across airports (e.g. LAX vs SNA)** always show the On-Time coverage ratio. Delay and peak statements are made on the reporting-carrier scope only and named as such.

## 5. Investment screening methodology [proposal, revised after critique]

### 5.1 What the score is — and is not
**"Terminal expansion opportunity screen."** It ranks where **the profit pool from additional passengers is largest**, then shows, as explicit flags, whether a terminal project could actually capture it. It is **not** a valuation: no costs, debt, airline-agreement economics (residual vs compensatory), PFC/AIP eligibility or construction risk. Every ranking output carries that sentence.

**Key design decision (from the critique): airfield congestion is not a positive score input.** A terminal renovation adds gates and processing capacity. It does not relieve runway, airspace, slot or curfew limits. High airfield strain therefore means more terminal capacity *may not add flights*. It is a **feasibility flag**, not opportunity. Delay and peak metrics stay in the congestion analysis (§4), not in this score.

### 5.2 Score definition (one expression, frozen in `config/screening.toml`)
```
score = 0.50 · S(incremental_enplanements)   # TAF FY2025→FY2035 absolute increase, log-anchored
      + 0.30 · S(realized_growth)             # T-100 T12 enplanements vs prior T12
      + 0.20 · S(cbsa_per_capita_income)      # yield / market-quality proxy (home CBSA)
S(x) = clip((x − lo) / (hi − lo), 0, 1) · 100   with pre-registered anchors:
        incremental_enplanements: log10 scale, 10^4 → 0, 10^7 → 100
        realized_growth:          −5% → 0, +10% → 100
        cbsa_per_capita_income:   $45k → 0, $110k → 100
```
**Why these three:**
- *Absolute* incremental passengers measure the profit pool: 10% growth at BOS is ~2M passengers, at MHT ~70k. That is the scale the investment case lives on. Using it once removes the separate size term and the growth double-count.
- Realized growth is evidence the forecast isn't just optimism.
- Income proxies yield and spend per passenger.

Each enters once, with no overlapping constructs. Population growth was dropped: TAF already embeds the socio-economic path.

**Anchored scales, not percentiles:** comparable across any query (New England or national), independent of peer-group size, interpretable ("growth +4% → 60 points"). The anchors are documented judgment, fixed before looking at rankings.

**Eligibility gate (not scored, listed with reason):** ≥ **500k** CY enplanements (investment scale, configurable); all three inputs present.

**Dry run on today's DB [measured]** with the formula above:
- National top 5: ORD 82.6, BNA 80.9, SFO 80.0, DEN 75.6, AUS 74.6. Spread across 233 airports: p10 19, median 44, p90 62.
- With a 100k gate, **Nantucket (ACK, 153k seasonal passengers) ranked #2 in New England** on resort-area income and volatile small-base growth. That is the reason for the 500k gate. Airports below it are returned as *"below investment scale"* with their raw metrics, never silently dropped.
- New England at ≥500k: BOS 69.3 › PWM 47.1 › HVN 45.1 › BDL 41.9 › PVD 40.8 › MHT 38.5 › BTV 36.1. HVN, BDL and PVD are within 3 points of each other, so they are **tied under these weights**. **No reweighting, no imputation.** A missing input means the airport isn't scored, and the reason is shown.

**Feasibility & risk flags (shown beside every rank, never hidden in the number):**
| Flag | Rule | Evidence class |
|---|---|---|
| `REGULATORY_CAP` | verified curated cap/curfew (e.g. SNA passenger cap) | observed (cited) |
| `AIRFIELD_BINDING` | reporting-carrier scheduled hour > verified IMC rate (lower-bound argument) | calculated |
| `AIRFIELD_UNKNOWN` | no verified capacity rate | not_established |
| `CARRIER_CONCENTRATION` | top operating carrier > 50% of seats (shown with the hub-tenant interpretation: lease anchor *and* de-hubbing risk) | calculated |
| `CAPITAL_CONTEXT` | NPIAS need and FY21–25 awarded grants, raw dollars (context, not scored) | estimated / observed |
| `LOW_COVERAGE` | On-Time coverage < 0.7 for any congestion statement | calculated |

**Sensitivity = named scenarios with exact rank changes** (replaces Dirichlet): base · equal weights · demand-only (incremental pax) · momentum-heavy (0.3/0.5/0.2). Output: rank per scenario and the max rank shift. Airports within **3 score points** are reported as *"tied under these weights"*.

**Explainability:** contributions are exactly additive (score = Σ weight·S), so `explain_rank(A, B)` lists the per-input point differences, which sum to the score gap. The LLM narrates; it doesn't compute.

**Optional profitability side column (decision §9):** FAA CATS debt per enplanement and cost per enplanement as a *financial-capacity* screen. **Not multiplied with TAF** (average revenue ≠ marginal profit) and not in the score.

**Alternatives rejected:** percentile normalization within hub class (coarse at n=30, not comparable across scopes); Dirichlet rank intervals (tuning noise presented as uncertainty); LLM-chosen weights (irreproducible); learned models (no labelled outcomes); multi-dimension composites with congestion as opportunity (wrong sign for a terminal thesis).

## 6. Unmet demand methodology [proposal, revised after critique]

Vocabulary enforced in outputs:
| Term | Meaning | Our measure | Class |
|---|---|---|---|
| **Served demand** | passengers carried | T-100 enplanements | observed |
| **Supply** | seats, departures, operations | T-100, ATADS | observed |
| **Capacity-tight service** | share of passengers flying on route-months with pax/seats ≥ 0.85 and ≥ 0.95, by stage-length band, plus trend | T-100 | calculated |
| **Airfield-constrained growth** | scheduled demand above modeled capacity in peak hours | On-Time schedule (lower bound) vs verified FAA rates | calculated (one-directional) |
| **Forecast demand** | FAA's unconstrained expectation | TAF | forecast |
| **Turned-away / latent / leaked demand** | travellers spilled, suppressed or using other airports | **not_established** with current data (needs DB1C / fares) | — |

**No spill solver.** Inverting a flight-level spill model (k ≈ 0.3–0.4 is a *departure*-level coefficient) on monthly route totals mis-specifies the variance and becomes unbounded as seat factor approaches 1. Instead we report capacity tightness distributions, which are observable and honest.

**The airfield argument, stated exactly:** the On-Time schedule covers only reporting carriers (SFO coverage 0.78), so it is a **lower bound** on total scheduled operations. If the lower bound already exceeds a verified IMC rate in some hours, total demand exceeds IMC capacity in those hours. The reverse can't be concluded. For SFO the engine reports:
- (a) the share of operating hours where reporting-carrier scheduled ops > 74 (IMC upper rate), a lower bound;
- (b) p95 = 66 < IMC 71–74, so in typical peaks the lower bound does **not** exceed IMC (inconclusive for total demand);
- (c) max = 82 > 74;
- (d) all of these are below the VMC rate of 104–107.

Conclusion template: *"In at least X% of hours the schedule exceeds IMC capacity, so delay concentrates on low-visibility days (consistent with NAS/weather delay minutes by month)."* That is a calculated finding plus a labelled hypothesis about cause.

**"Why" answers** are hypotheses with evidence for and against, each citing findings. The engine never outputs "SFO has N unmet passengers".

## 7. Reliability strategy [proposal]

**Failure behaviour (typed, never silent):** `OutOfCoverage(available_range)`, `AmbiguousEntity(candidates)`, `NotApplicable(reason)` (e.g. ATADS for an untowered airport), `InsufficientData(min_required, found)`, `SourceConflict(values, sources)` (e.g. ACAIS vs T-100 > 3%: report both, prefer the documented primary, flag). Each becomes a `not_established` finding the agent must relay.

**Testing pyramid (analytical correctness, not just code):**
1. **Formula unit tests** on synthetic mini-DBs with hand-computed answers (seat factor, Σ/Σ vs mean-of-ratios, growth windows, anchored-scale clipping, tightness shares, IMC inequality logic).
2. **Golden-value regression** on the seed DB (ANC long-haul Jul-2026 = 23.1%; T-100 vs ACAIS ratio; SFO p95 hour = 66), pinned to the raw fingerprint.
3. **Invariants / property tests**: shares ∈ [0,1]; S(x) monotone and clipped; scores ∈ [0,100]; contributions sum exactly to the score (additive by construction); no airport scored with a missing input.
4. **Metamorphic tests**: scaling all weights leaves the ranking unchanged; adding an airport outside the peer group leaves peer scores unchanged; renaming a code (PBI/DJT) leaves results unchanged.
5. **Cross-source consistency** (already partly in coverage): T-100 vs ACAIS, ATADS vs TAF history, T-100 ops vs ATADS commercial ops.
6. **Coverage/edge tests**: window outside range → `OutOfCoverage`; untowered airport → `NotApplicable`; airport without county → econ dimension missing, not zero.
7. **Sensitivity report** checked into docs: rank stability of the top-10 under perturbation.
8. **Independent verification**: Grok re-derives 3–5 headline numbers from raw SQL without using the engine; mismatches block release.

## 8. Agent integration (Phase 3 preview) [proposal, revised]

- **Five tools**:
  - `resolve_airports(text)` → airport_ids plus resolution notes;
  - `get_metrics(airports, metric_ids, window)`, with parameterized ids such as `long_haul_share:3000:passenger`;
  - `rank_airports(scope, scenario)` → scores, contributions, flags, not-scored list, scenario rank table;
  - `explain_rank(a, b)`;
  - `analyze(airport(s), topic ∈ {congestion, demand_pressure, investment_context})`.

  Results are JSON with `findings[]`.
- **Resolution policy (deterministic, in the resolver):**
  - A contrast question binds each side to its most specific airport ("LA vs Santa Ana" → LAX vs SNA) and lists the excluded basin airports in the answer.
  - It asks for clarification only when the candidates are comparable in size and the question isn't a contrast.
  - Gate exclusions are returned explicitly, never silently dropped.
- **Loop:** plain Claude tool use (Anthropic SDK), no framework and no separate planning turn. Multi-part questions are handled by the model calling several tools.
- **Grounding by construction:**
  - The model writes the answer with **finding placeholders** (`{F3.value}`, `{F3.period}`).
  - Code renders the values, and unknown ids fail rendering, with the tool table shown instead.
  - Allowed derived numbers (differences, ratios) are computed by a small `derive(op, F_a, F_b)` tool, not by the model.
  - Follow-up turns can reference findings from earlier turns, which are kept in session state.
  - Caveat codes attached to used findings are appended automatically.
- **UI:** a minimal web chat (FastAPI + static page) rendering finding tables, score contributions and flags. Voice through the browser Web Speech API is a cheap bonus if time remains.

## 9. Implementation priorities (revised)

**Build first: golden fixtures for the four questions.** For each, hand-write the expected *shape* and key values from SQL:
- ANC: passenger and freight long-haul rows;
- LAX vs SNA: delay and peak with coverage ratio, cap/curfew flags;
- New England: ranking, flags and not-scored list;
- SFO: tightness distribution, the IMC inequalities, TAF.

The engine is done when it reproduces them and answers 2 unscripted questions.

**Then:** core (lightweight `Finding` dataclass with lineage, resolver, windows) → ~12 metrics → `analyze` topics → screening (TOML, scenarios, explain) → 5 tools + CLI.

**Decision point for you — profitability side column:** ingest FAA CATS (debt per enplanement, cost per enplanement) as a small source? It adds a financial-capacity column that interviewers expect to see, but it doesn't change the score. Without it, the system answers *expansion opportunity* and says so.

**Defer:** DB1C (fares/O&D/leakage, the true unmet-demand data), verified FAA capacity rates for more airports (FAA 2019 profiles, 30 core airports; high value for the `AIRFIELD_BINDING` flag), terminal-capacity verification for demo airports, Git LFS.

**Cut:** Dirichlet sensitivity, correlation auto-merge, A–D quality grades (caveat codes + coverage ratio instead), spill solver, ASV, TPHP, a planning turn, regex grounding loop, text-to-SQL, ML models, valuation, multi-agent orchestration, frameworks.

## 10. Tradeoffs summary
| Choice | Why | Cost / limitation |
|---|---|---|
| Deterministic engine + coarse tools | reproducible, testable, small tool surface | less flexible than text-to-SQL; new questions may need a new metric (cheap via catalog) |
| Anchored scales (pre-registered) | comparable across any scope, interpretable | anchors are judgment; documented and scenario-tested |
| Fixed default weights + sensitivity | defensible, transparent | weights remain judgment; made explicit and stress-tested |
| Capacity-tightness distributions instead of spill estimates | observable, no mis-specified model | turned-away demand stays not_established (needs DB1C) |
| Airfield strain as flag from verified rates only | right sign for a terminal thesis; no fake precision | most airports `AIRFIELD_UNKNOWN` until more FAA profiles are curated |
| Size-aware demand term (absolute incremental pax) | matches the profit pool | favours large airports by design; momentum and income terms plus the scale gate balance it |
| Placeholder-grounded answers | the model cannot type an unbacked number | slightly stiffer prose; derived numbers go through `derive()` |

## 11. Independent critique (Grok): disposition

| Critique | Decision |
|---|---|
| Airfield congestion is the wrong sign for a terminal thesis; slots/curfews not relieved | **Accepted**: congestion moved out of the score into feasibility flags (§5.1) |
| Renormalizing weights rewards missing evidence | **Accepted**: no reweighting; missing input = not scored, reason listed |
| Hub-class percentiles coarse (n=30), not comparable across scopes | **Accepted**: pre-registered anchored scales |
| Dirichlet intervals are tuning noise | **Accepted**: named scenarios with exact rank shifts |
| NPIAS need rewards sponsor optimism; grant ratio sign wrong | **Accepted**: context column only |
| Growth/size/busyness double-counted; HHI sign | **Accepted with change**: one demand-scale term = *absolute* incremental passengers (deliberately size-aware: profit pool), plus realized growth; HHI → flag |
| Spill inversion on route-month totals invalid, unbounded near SF=1 | **Accepted**: replaced by capacity-tightness distributions |
| Peak vs capacity mixes traffic scopes; SFO sentence overstated | **Accepted**: lower-bound, one-directional inequality stated exactly |
| ASV from runway count misreads AC 150/5060-5 | **Accepted**: dropped |
| TAF × revenue ≠ profit | **Accepted**: CATS only as an optional financial side column |
| Metric definition issues (load factor naming, long-haul weighting, route churn, carrier HHI, NAS denominator, taxi spread, TPHP) | **Accepted**: §4 revised |
| Over-engineering | **Mostly accepted**: cut list in §9. Kept: lightweight evidence record and resolver, the minimum for trustworthy answers |
| Engine can't answer the four questions on demo day | **Accepted**: golden fixtures first |
| Regex grounding validator false positives/negatives | **Accepted, better design**: placeholder rendering, so the model never types critical numbers |
| 12 overlapping tools; ambiguity policy | **Accepted**: 5 tools, deterministic resolution policy |
| Test invariants contradict algebra | **Accepted**: additive score, flags not multipliers, frozen universe snapshot |

## 12. Concrete implementation plan (for approval)

| Stage | Deliverable | Done when |
|---|---|---|
| **2.0 Golden fixtures** | expected outputs for the four questions, written from raw SQL (Grok re-derives independently) | fixtures committed; disagreements resolved |
| **2.1 Core** | `airport_analytics/core`: `Finding` dataclass with automatic lineage from `ingest_manifest`; resolver with contrast/ambiguity policy; windows + typed errors (`OutOfCoverage`, `AmbiguousEntity`, `NotApplicable`, `InsufficientData`) | resolver tests (LA/Santa Ana, New England, PBI/DJT), coverage errors |
| **2.2 Metrics** | ~12 metric ids from §4 (Σ/Σ, named windows, caveat codes, coverage ratio) | formula tests on a synthetic mini-DB + golden values |
| **2.3 Analyses** | `analyze` topics: congestion (scoped + coverage), demand_pressure (tightness + IMC inequalities + TAF), investment_context; long-haul via metric ids | the four fixtures reproduce; 2 unscripted questions answered |
| **2.4 Screening** | `config/screening.toml`, anchored scales, gate, flags, scenarios, `explain_rank` | additive-contribution test, gate/no-imputation tests, scenario table in docs |
| **2.5 Tools + CLI** | 5 ToolSpecs with JSON schemas and input validation; CLI JSON output | every tool callable from CLI; schema validation tests |
| **2.6 Docs** | architecture doc: scoring methodology, tradeoffs, where AI is used | reviewed |
| *(optional)* | FAA CATS side column | your decision |
| **Phase 3** | agent loop, placeholder-grounded answers, chat UI, optional voice | end-to-end demo incl. follow-ups |

Estimated effort: Stages 2.0–2.5 ≈ 5–6 focused hours; Phase 3 ≈ 3–4 hours.
