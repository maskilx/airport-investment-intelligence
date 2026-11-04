# Analytics Engine & Agent Tool Architecture (Phase 2 — decision record)

Status: **adopted for implementation** · Date: 2026-11-04 · Supersedes the tool list in [04](04-phase2-analytics-plan.md) §8; keeps its metric, scoring and unmet-demand methodology.

## 1. The problem with "five tools"

`get_metrics / rank / explain / analyze(topic)` answers the questions we anticipated. It cannot express *"does
population growth relate to passenger growth across Southeast medium hubs?"*, *"which airports had unusual
traffic drops this year?"* or *"how good was FAA's FY2025 forecast?"* without a new tool each time. The
requirement is composition, not a longer tool list.

## 2. Options considered

| Option | Flexibility | Correctness control | Lineage | Verdict |
|---|---|---|---|---|
| A. Many purpose-built tools | low | high | easy | ❌ every new question = new code |
| B. LLM writes SQL over views | very high | **low**: denominators, grain, double counting and window alignment become the model's job | hard | ❌ as primary path |
| C. **Semantic layer + constrained analysis spec (JSON DSL)** compiled to SQL by the engine | high: any metric × entity set × window × grouping × operation | **high**: formulas defined once, validated specs, engine-owned aggregation | automatic | ✅ **primary** |
| D. C plus a guarded read-only SQL tool | highest | results labelled `exploratory`, never silently mixed with catalog metrics | from referenced views | ✅ **escape hatch** |

**Decision: C + D.** This is the "semantic layer" pattern (metrics defined once as ratios of additive
measures, queried by dimensions), as used by BI metric stores, plus a typed set of analytical operators.
The LLM's job becomes choosing *what* to compute (a small JSON spec). The engine owns *how*.

## 3. Semantic layer (`airport_analytics/semantic.py`, versioned `CATALOG_VERSION`)

* **Fact sources**: each is one conformed view with a declared grain, an airport key, a time key and
  supported dimensions. Examples:
  - `t100_dep`: departing segments → enplanement side;
  - `t100_arr`;
  - `ontime_dep` / `ontime_arr`;
  - `atads`;
  - `taf_enp` / `taf_ops` (forecast vs historical);
  - `acais`;
  - `area_econ` (BEA via the airport's home CBSA/county);
  - `grants`, `npias`.
* **Measures**: additive aggregates on one fact, with built-in filters (e.g. `passengers` = Σpax on
  passenger/combi rows). Non-additive measures (median taxi, quantiles) are flagged and computed only at query grain.
* **Metrics**: expressions over measures, *always ratio-of-sums at the requested grain*
  (`seat_factor = passengers / seats`), with unit, epistemic class, definition text, caveat rules and
  parameters (`long_haul_share{min_miles, weight}`). Metrics may reference metrics (composition).
  Each metric has a stable id and a `formula_version`. Changing semantics means a new version; old results stay interpretable.
* **Dimensions**:
  - airport attributes: code, state, division, region, hub class, CBSA, towered;
  - time: month, CY, FY;
  - carrier, destination, distance band, international, service type, ATADS user class, hour of day.

  A metric declares the dimensions it supports, and an unsupported grouping is a typed error, not a wrong number.
* **Area-level measures** (population, income) attach to an airport through its home CBSA. Group
  totals aggregate **distinct areas**, so two airports in one CBSA are never double-counted.

## 4. Analysis spec (the agent's "language")

```json
{ "op": "aggregate | change | trend | rank | correlate | anomaly | distribution | forecast_vs_actual | screen",
  "metrics": ["seat_factor", {"id": "long_haul_share", "params": {"min_miles": 3000, "weight": "passengers"}}],
  "entities": {"airports": ["LAX", "SNA"]}  |  {"group": {"census_division": "New England", "min_enplanements": 500000}},
  "group_by": ["airport", "month"],
  "window": {"t12": true} | {"start": "2025-01", "end": "2025-12"} | {"cy": 2025} | {"fy": 2025},
  "compare_window": {...},            // for change
  "filters": {"international": false, "service_type": ["passenger"]},
  "options": {...op-specific...} }
```
Validation before execution:
- metric ids and parameters must exist;
- every dimension must be supported;
- the window must be inside the coverage of every fact used (else `OutOfCoverage` with the available range);
- entity sets must be non-empty;
- result sizes are bounded.

Each operator is deterministic Python over engine-computed frames:
| op | Computes | Guards |
|---|---|---|
| aggregate | metric values per group | coverage ratio attached for On-Time metrics |
| change | window vs compare_window, absolute and % | identical window lengths; identity spliced by airport_id |
| trend | monthly series, YoY, OLS slope, CAGR | min points; seasonality caveat |
| rank | order by one metric or a weighted composite of chosen metrics (dynamic criteria), anchored or set-relative scaling (declared) | ties within tolerance reported |
| correlate | Pearson + Spearman across entities, n, deterministic bootstrap CI | n ≥ 8, otherwise `InsufficientData`; "association ≠ causation" caveat |
| anomaly | robust z (median/MAD) of YoY change by month, or cross-sectional outliers | MAD = 0 handled; flags only |
| distribution | quantiles across a group | — |
| forecast_vs_actual | TAF FY forecast vs actual FY (T-100 enplanements, ATADS ops) | only years where the forecast is a forecast |
| screen | screening model (04 §5): anchored scales, gate, flags, named scenarios, additive contributions | no imputation; not-scored list |

## 5. Evidence & grounding (architectural, not prompt-based)

1. **Findings**: every number the engine returns is a `Finding` stored in a session `EvidenceStore` with
   id (`F17`), value, unit, epistemic class, metric id and formula version, entity, window, sources
   (source ids, periods, vintage ids from `ingest_manifest`), coverage, caveats and the reproducing spec.
   A finding can be re-executed from its spec (`reproduce F17`).
2. **Derived numbers** (differences, ratios between findings) come only from a `derive` tool, which creates a
   finding whose inputs are recorded.
3. **Answer = structured object**: `{headline, body (markdown with {F17} placeholders), claims:[{kind:
   fact|inference|hypothesis, text, support:[F…]}], assumptions, limitations}`.
4. **Validator** (deterministic, runs before anything is shown):
   - every placeholder resolves;
   - prose outside placeholders contains **no numerals** except allowlisted tokens (years, FY/CY labels, airport codes);
   - every `fact`/`inference` claim cites at least one finding;
   - hypotheses are labelled;
   - caveats of the cited findings can't be dropped.
   Failure returns a precise error to the model (bounded retries). If the retries fail, the evidence table renders without narrative.
5. **Renderer** fills values with unit formatting and appends, automatically:
   - an evidence table (value, class, definition, source, period, vintage, coverage);
   - the methodology notes of the metrics used;
   - caveats.
   Forecast, estimate and hypothesis classes are visibly labelled. The model never types a critical number.
6. **Exploratory SQL** results carry class `exploratory` plus the SQL text, and render with that label.

## 6. Agent workflow (provider-agnostic)

`agent/loop.py` drives any `ModelBackend` (Anthropic adapter, or a scripted backend for tests):
1. resolve entities (resolver policy: contrast questions bind each side; ambiguity → clarification);
2. optionally read the catalog;
3. run one or more analysis specs;
4. derive if needed;
5. compose the structured answer;
6. validate, then render.

Multi-part questions are just several specs. The model decides when to ask for clarification, but the resolver
and the `OutOfCoverage` / `NotApplicable` / `InsufficientData` errors make the need explicit.

## 7. Tools exposed to the model

| Tool | Purpose |
|---|---|
| `resolve_entities` | text → airport_ids / groups, with ambiguity and exclusion notes |
| `describe_catalog` | metrics, parameters, dimensions, operators, coverage windows |
| `run_analysis` | execute one analysis spec, returning findings + a compact table |
| `derive` | difference / ratio / share between findings |
| `query_sql` | read-only, whitelisted views, row-capped, `exploratory` class |
| `compose_answer` | validate and render the final answer |

Six tools, of which one (`run_analysis`) carries the flexibility. New questions need no new tools. New
measures or metrics are catalog entries.

## 8. Testing & evaluation

* **Engine correctness**:
  - formula tests against independent hand-written SQL (Grok-authored oracles);
  - golden values;
  - typed-error tests (coverage, unsupported dimension, insufficient n).
* **Generated property tests**: random valid specs from the catalog are checked for invariants:
  - group ratio = Σnum/Σden of its members;
  - CY = Σ months for additive measures;
  - compare(A,B) = aggregate(A), aggregate(B);
  - historical-code aliases give identical results;
  - rank order matches values;
  - change = difference of two aggregates;
  - area measures are never double-counted;
  - spec → finding → reproduce gives the same value.

  This measures **generalization of the engine** to specs nobody wrote by hand.
* **Grounding tests**: the validator rejects numerals, unknown ids, unsupported facts, and dropped caveats.
* **Agent evaluation set** (`eval/questions.jsonl`), categories:
  known, held-out unseen, multi-step, ambiguous, unanswerable, adversarial. Each item has machine-checkable
  expectations (entities, ops or metrics used, must-refuse, numeric checks against oracle findings).
  Generated from the catalog by template + LLM paraphrase (Gemini), with a held-out split never used in development.
  In this phase Grok acts as the agent through the CLI tools. The Anthropic backend runs the same set once an API key exists.

## 9. Boundaries
`airport_data` (ingestion, unchanged contract) → `airport_analytics` (engine, tools, evidence; no LLM) →
`airport_agent` (loop, backends, prompts). No new runtime dependencies; the Anthropic SDK is optional,
for the backend only.
