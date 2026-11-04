# Airport Investment Intelligence Agent: Architecture

An analyst workspace for **airport modernization screening and due diligence**. You ask questions in natural
language. Every number in an answer is a traceable finding, computed by a deterministic engine over public data, and
every claim is typed and checked against the evidence it cites. The LLM plans and explains. It never computes, never
writes a number, and never decides on its own that a comparison, ranking or cause holds.

The system separates three questions:
* **Stage A, passenger growth opportunity.** Built: the screen in §2.
* **Stage B, whether a terminal intervention addresses an actual constraint.** Flags and evidence-graded constraint records are built. The assessment itself is not.
* **Stage C, project economics.** Not built.

It does not claim that an expansion is profitable. The reconciliation of the independent reviews and the plan are in
[docs/10](docs/10-architecture-assessment.md).

```
 17 registered sources*         deterministic core                                 AI layer               product
 BTS T-100, On-Time          ┌───────────────────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
 FAA ATADS, ACAIS, TAF,      │ raw vintages (sha256)     │   │ semantic     │   │ agent runtime    │   │ FastAPI SSE  │
 NPIAS, grants, NASR,   ───► │ validation (blocking)     ├──►│ layer +      ├──►│ (provider-       ├──►│ workspace UI │
 Census CBSA, BEA,           │ DuckDB conformed views    │   │ analysis DSL │   │  agnostic loop)  │   │ charts,      │
 OurAirports, curated        └───────────────────────────┘   │ → Findings F#│   │ memory, web W#   │   │ evidence,    │
                                                             └──────┬───────┘   └────────┬─────────┘   │ voice        │
                                                                    └── grounding validator ◄┘          └──────────────┘
```
\* public bulk files and reporting-form exports (BTS, FAA, Census, BEA, OurAirports), plus curated and reference tables.
They are not 17 live APIs.

## 1. Layers and why each exists

| Layer | Code | Purpose | Why not simpler / heavier |
|---|---|---|---|
| Data foundation | `src/airport_data` | Immutable, vintaged raw archive with sha256 → validation → atomic DuckDB build; airport identity keyed on BTS `airport_id` with crosswalks | Reproducibility and lineage are prerequisites for "clickable evidence". DuckDB is embedded and fast, with no server. |
| Semantic layer | `airport_analytics/semantic.py` | Facts → additive measures → metrics, evaluated as ratio-of-sums at the requested grain. Period, coverage and caveats are attached. | Stops the classic errors: averaging ratios, summing area values, mixing stocks and flows. |
| Analysis DSL | `analysis.py`, `screening.py` | JSON specs with ops `aggregate, rank, correlate, trend, anomaly, distribution, forecast_vs_actual, screen` plus transforms `pct_change, abs_change, cagr` | The model composes analyses instead of writing SQL, and specs are validated with typed errors. `query_sql` exists as an AST-whitelisted escape hatch labelled *exploratory*. |
| Evidence | `evidence.py` | A `Finding` per number: value, unit, class (observed / calculated / forecast / estimated / exploratory), definition, window, sources and vintages, caveats, inputs. Each finding also carries an **execution envelope** (tool, op, full original spec, resolved airport ids, catalog version, screening config hash, scenario, as-of date, data build fingerprint), the **assumptions** it was produced under, and a **status** (current or stale). | The single source of numeric truth. `get_finding(reproduce)` replays the *original* operation and reports `match`, `build_same`, `entity_set_same` and `config_same`. |
| Traceability | `render.py` | `compose_answer` validates `{F#}` placeholders. It rejects literal numbers, number words, Unicode numerals, a finding cited next to a different airport, and stale findings. Evidence, methodology and caveats are appended automatically. | Guarantees *where a number came from*. It does not show that the number supports the sentence; claim validation does that. |
| Claim validation | `claims.py` | Typed claims, each with deterministic requirements: `fact`, `comparison` (same metric, unit, class and period; relation checked against the values; a 5% band means "similar"), `ranking` (must come from a rank or screen op; code writes rank, set size and scenario robustness), `inference`, `hypothesis` (indicator findings plus competing explanations), `financial` (needs a `financial_model` finding; none exists, so always rejected), `external`. Vocabulary gates cover headline, body and caveats. Years must be periods of cited findings. | The model chooses *what* to claim; code decides whether the evidence supports that kind of claim. The vocabulary gate is defence in depth: paraphrase can evade it. The structural checks are the guarantee. |
| Agent runtime | `airport_agent/runtime.py` | Tool loop with step, tool-call, wall-clock and cancellation budgets, checked before every tool. DuckDB is interrupted mid-query on timeout or cancel. Every `tool_use` gets a paired result. Each provider request has a hard context cap that compacts old tool bodies to finding ids. Events and traces. A final answer must pass validation, or be a number-free clarification. | Custom (~400 lines) rather than a framework: the invariants above live in the loop, and every framework surveyed would have to be worked around. |
| Memory | `memory.py`, `assumptions.py` (decision record: [docs/08](docs/08-memory-and-context.md)) | SQLite transcript, persisted findings with stable ids, structured state, number-free rolling summary, BM25 recall, token-budgeted context. **Assumption dependencies:** an assumption may bind a parameter (`long_haul_share.min_miles = 2400`, a screen scenario), and findings computed with any other value become stale. Superseding an unbound assumption stales the findings produced under it. Staleness propagates through `derive`. | No vector DB or memory framework. All of them store LLM paraphrases, which would violate "a summary is never a source of numbers". Memory text is number-masked. |
| Web research | `web.py` | `web_search` + SSRF-guarded `fetch_page` produce W# external evidence, separate from F#. Web numbers are allowed only inside quotes verified verbatim against the fetched text. | Keeps internal facts and external claims visibly distinct, and auditable. |
| Models | `models.py`, `offline.py` | One `ModelBackend` protocol. **Gemini** (REST, opt-in, request budget, usage log, no fallback), a scripted backend for tests, and a deterministic **offline planner** for demos with zero model calls | Cost safety by construction. The offline planner exercises the full stack in tests and the UI. |
| API + UI | `airport_app/server.py`, `web/` | FastAPI with SSE streaming (tool strips live), conversations, cancellation, a provenance endpoint and a memory inspector. Vanilla ES-module UI with vendored Vega-Lite | No build toolchain. Charts are built server-side from findings, so the browser never computes a number. |

## 2. Scoring methodology: Passenger Growth Opportunity Screen (stage A)

`op=screen` is defined in `config/screening.toml` (versioned `model_version = 1.0`). It ranks **passenger growth
opportunity**: forecast increase, realized growth and market income.

It does **not** establish:
* that a terminal is the binding constraint (runway capacity is not terminal capacity, and high load factors are not denied demand);
* project returns.

Weights and anchors are analyst assumptions, not fitted predictors of return. Earlier versions of this document
called it a "terminal-expansion screen", which overclaimed.

* **Gate:** airports with fewer than 500k annual enplanements (FAA ACAIS, latest calendar year) are listed as below investment scale and not scored.
* **Components** are scaled to 0–100 on *fixed anchors*. Fixed anchors make scores comparable across regions and runs; they are not min-max scaled within the result set.

| Component | Metric | Scale | Anchors | Base weight |
|---|---|---|---|---|
| Projected passenger increase | FAA TAF enplanements FY2035 − FY2025 (absolute) | log10 | 10k → 0, 10M → 100 | 0.50 |
| Realized growth | T-100 passengers, trailing 12 months vs prior 12 | linear | −5% → 0, +10% → 100 | 0.30 |
| Market strength | Home-CBSA per-capita income (BEA, latest year) | linear | $45k → 0, $110k → 100 | 0.20 |

* **Flags** are reported, never hidden in the score. They come from curated constraint records evaluated at an explicit **as-of date**, which is recorded for replay. Each record has an evidence level: `primary`, `secondary`, `snippet` or `unverified`.
  * `REGULATORY_CAP` / `CURFEW`: in effect at as-of, with primary or secondary evidence. Expired caps are excluded and listed.
  * `REPORTED_CONSTRAINT_UNVERIFIED`: in effect, but with only snippet or unverified evidence. Shown, never treated as fact.
  * `AIRFIELD_BINDING` / `AIRFIELD_HEADROOM_IMC`: scheduled peak against the highest primary- or secondary-verified instrument-conditions rate, in at least 5% of operating hours. The rate must be a strict number or range in operations/hour. Free text is never mined for numbers.
  * `AIRFIELD_UNKNOWN`: no usable verified rate.
  * `CARRIER_CONCENTRATION`: the largest carrier holds more than 50% of seats.
* **Explaining a score:**
  * Every airport's score is split into one *calculated* finding per factor (weight × anchored points), so each answer shows `score = Σ contributions`, and each contribution links to its input finding and source file.
  * The ranking claim names the largest contributor and the rank range across scenarios. Code writes both.
  * Every answer that cites a screen score carries a **"How the score is calculated"** section. It is generated from `config/screening.toml`, never written by the model, and covers purpose, factors, weights, anchors, eligibility, missing-data rule, ties, scenarios and flags.
* **Robustness:**
  * Each airport's rank is reported under four weight scenarios: base, equal, demand-only and momentum-heavy, with the maximum rank shift.
  * Gaps under 3 points are reported as ties.
* **Other answers:**
  * Congestion uses airside indicators: delay rate, taxi-out, scheduled peak hour (p95), tower operations, NAS delay per arrival. Coverage is shown because On-Time covers only reporting carriers on domestic flights.
  * Long-haul share is parameterised (threshold, departure- vs passenger-weighted), and alternatives are shown when the definition is open.
  * "Unmet demand" is **never** presented as measured. The agent reports indicators (seat factor, share of capacity-tight routes, peak pressure, TAF vs actual, carrier concentration) and labels the causal story a hypothesis.

## 3. Where AI is used, and where it is not

| Step | Who | Notes |
|---|---|---|
| Understanding the question, choosing entities, metrics, periods and ops | LLM (Gemini) | Tool calls validated against the catalog. Ambiguity triggers a clarification ("Portland" → PDX or PWM). |
| Resolving places | deterministic resolver | Aliases, codes, "City, State", regions. Ambiguity is returned, never guessed. |
| Every computation and number | deterministic engine | DuckDB SQL compiled from the semantic layer. |
| Arithmetic between results | `derive` tool | Recorded as a new finding with inputs. |
| Writing the explanation | LLM | Placeholders only. Every assertion is a typed claim. Code verifies comparison directions and compatibility, writes ranks, requires competing explanations for causal stories, and rejects financial claims (no economics model). |
| Assumptions and corrections | LLM proposes; code enforces | `update_memory` with `binds`. Dependent findings go stale and cannot be cited. |
| Labelling what kind of knowledge a statement is | deterministic | Claim tags come from claim type and evidence class: Measured, Calculated, Forecast (FAA), Comparison or Ranking (computed), Interpretation, Hypothesis, External source. Values that are not established are listed under Limitations with the reason, never shown as facts. |
| Charts | deterministic | ChartSpec (findings + type + validated title) → Vega-Lite. |
| Memory updates | deterministic + validated tool | State is updated from tool calls. `update_memory` records assumptions and corrections; summaries are number-free. |
| Web context | LLM chooses pages; code verifies quotes | |

## 4. Key trade-offs

* **Deterministic core vs flexibility.** The DSL covers most questions: in the generated evaluation, the failures were step-budget exhaustion, not missing operators. `query_sql` handles the long tail, labelled exploratory. The cost is maintaining the semantic layer, and the benefit is that every number is reproducible.
* **Custom loop vs agent framework.** About 300 lines that we fully control and test with scripted models. We forgo framework conveniences such as built-in tracing UIs.
* **Lexical memory vs embeddings.** References in this domain are codes, names and ids, where exact matching wins. No embedding calls means no cost and no extra service. The upgrade path is SQLite FTS5, then embeddings behind the same `retrieve()` signature.
* **Data freshness vs reproducibility.** Answers carry periods and vintages. A rebuild from the committed raw archive is bit-for-bit identical, and new vintages are additive.
* **Public data limits, stated rather than papered over.** There is no fare, spill or booking data, so unmet demand is inferred, not measured. On-Time is domestic and reporting carriers only, so coverage is shown. TAF is an unconstrained FAA forecast. Terminal capacity (gates, square feet) is not in public structured data; web research can add cited context, but not "facts".
* **Typed claims vs free prose.** Comparisons and rankings are rendered by code, so the model cannot get a direction or rank wrong. The cost is less fluent prose. Vocabulary gates catch common overclaims ("guaranteed", "profitable", "needs more gates", "because"), but a determined paraphrase can evade a lexicon. That residual risk is accepted and documented, rather than hidden behind an LLM judge that would itself be unverifiable.
* **Over-invalidation vs silent staleness.** An unbound assumption change stales everything produced under it. Re-running is cheap; citing a finding computed under a superseded definition is not.
* **Context budget.** The hard cap uses a conservative 3 chars/token estimate (real tokenizers average about 4). Exact provider token counting is a network call, deferred until live use.
* **Voice.** Browser Web Speech (recognition + synthesis) drives the same agent at zero cost. A real-time voice stack (e.g. Pipecat + WebRTC) is the documented upgrade path ([docs/07](docs/07-product-phase-plan.md)).

## 5. Quality evidence

* **Tests (offline, no model calls):**
  * data pipeline, golden analytics values, typed errors, property tests;
  * regressions from two independent adversarial reviews;
  * memory: a 120-turn budget test and a poisoned summariser;
  * runtime with scripted and mocked-Gemini backends, the API over SSE, web SSRF and quote checks.
* **Reviews:**
  * Grok 4.7: data audit (16 findings), engine adversarial review (18), product-layer review (19). Logged in [docs/06](docs/06-phase2-audit-review-log.md) and [docs/reviews](docs/reviews/grok-product-review-2026-11-04.md).
  * An independent product and architecture review.
  * Both are reconciled against the code in [docs/10](docs/10-architecture-assessment.md).
* **Agent evaluation:** 49 of 70 generated questions were scored before the run was stopped, with 47 passing. The planner was Grok through its CLI, **not** this product loop with Gemini. The 21 unrun questions include all 10 adversarial questions. This is evidence, not a benchmark result ([docs/06](docs/06-phase2-audit-review-log.md)).
* **Not yet demonstrated:** a live Gemini run through this loop. It needs explicit authorisation and a request budget.
