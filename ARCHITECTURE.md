# Airport Investment Intelligence Agent: Architecture

An analyst workspace for a firm that invests in US airport modernization. You ask questions in natural language
and get answers where **every number is a traceable finding** computed by a deterministic engine over public data.
The LLM plans and explains. It never computes, and it never writes a number.

```
 public data (17 sources)        deterministic core                                 AI layer               product
 BTS T-100, On-Time          ┌───────────────────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
 FAA ATADS, ACAIS, TAF,      │ raw vintages (sha256)     │   │ semantic     │   │ agent runtime    │   │ FastAPI SSE  │
 NPIAS, grants, NASR,   ───► │ validation (blocking)     ├──►│ layer +      ├──►│ (provider-       ├──►│ workspace UI │
 Census CBSA, BEA,           │ DuckDB conformed views    │   │ analysis DSL │   │  agnostic loop)  │   │ charts,      │
 OurAirports, curated        └───────────────────────────┘   │ → Findings F#│   │ memory, web W#   │   │ evidence,    │
                                                             └──────┬───────┘   └────────┬─────────┘   │ voice        │
                                                                    └── grounding validator ◄┘          └──────────────┘
```

## 1. Layers and why each exists

| Layer | Code | Purpose | Why not simpler / heavier |
|---|---|---|---|
| Data foundation | `src/airport_data` | Immutable, vintaged raw archive with sha256 → validation → atomic DuckDB build; airport identity keyed on BTS `airport_id` with crosswalks | Reproducibility and lineage are prerequisites for "clickable evidence". DuckDB is embedded and fast, with no server. |
| Semantic layer | `airport_analytics/semantic.py` | Facts → additive measures → metrics, evaluated as ratio-of-sums at the requested grain. Period, coverage and caveats are attached. | Stops the classic errors: averaging ratios, summing area values, mixing stocks and flows. |
| Analysis DSL | `analysis.py`, `screening.py` | JSON specs with ops `aggregate, rank, correlate, trend, anomaly, distribution, forecast_vs_actual, screen` plus transforms `pct_change, abs_change, cagr` | The model composes analyses instead of writing SQL, and specs are validated with typed errors. `query_sql` exists as an AST-whitelisted escape hatch labelled *exploratory*. |
| Evidence | `evidence.py` | A `Finding` per number: value, unit, class (observed / calculated / forecast / estimated / exploratory), definition, window, sources and vintages, caveats, inputs, reproducing spec | The single source of numeric truth. Everything downstream cites ids. |
| Grounding | `render.py` | `compose_answer` validates `{F#}` placeholders. It rejects literal numbers, number words, Unicode numerals, a finding cited next to a different airport, and quantitative hypotheses. Evidence, methodology and caveats are appended automatically. | A guarantee instead of a prompt instruction. |
| Agent runtime | `airport_agent/runtime.py` | Tool loop with step, tool, wall-clock and cancellation budgets, an event stream and traces. A final answer must pass the validator, or be a number-free clarification. | Custom (~300 lines) rather than a framework: the invariants above live in the loop, and every framework surveyed would have to be worked around. |
| Memory | `memory.py` (decision record: [docs/08](docs/08-memory-and-context.md)) | SQLite transcript, persisted findings with stable ids, structured state, number-free rolling summary, BM25 recall, token-budgeted context | No vector DB or memory framework. All of them store LLM paraphrases, which would violate "a summary is never a source of numbers". |
| Web research | `web.py` | `web_search` + SSRF-guarded `fetch_page` produce W# external evidence, separate from F#. Web numbers are allowed only inside quotes verified verbatim against the fetched text. | Keeps internal facts and external claims visibly distinct, and auditable. |
| Models | `models.py`, `offline.py` | One `ModelBackend` protocol. **Gemini** (REST, opt-in, request budget, usage log, no fallback), a scripted backend for tests, and a deterministic **offline planner** for demos with zero model calls | Cost safety by construction. The offline planner exercises the full stack in tests and the UI. |
| API + UI | `airport_app/server.py`, `web/` | FastAPI with SSE streaming (tool strips live), conversations, cancellation, a provenance endpoint and a memory inspector. Vanilla ES-module UI with vendored Vega-Lite | No build toolchain. Charts are built server-side from findings, so the browser never computes a number. |

## 2. Scoring methodology (terminal-expansion screen)

`op=screen` is defined in `config/screening.toml` (versioned `model_version = 1.0`). It is a **screening rank of
expansion opportunity, not a valuation**: costs, debt, airline agreements and construction risk are not modelled, and the answer says so.

* **Gate:** airports with fewer than 500k annual enplanements (FAA ACAIS, latest calendar year) are listed as below investment scale and not scored.
* **Components** are scaled to 0–100 on *fixed anchors*. Fixed anchors make scores comparable across regions and runs; they are not min-max scaled within the result set.

| Component | Metric | Scale | Anchors | Base weight |
|---|---|---|---|---|
| Projected passenger increase | FAA TAF enplanements FY2035 − FY2025 (absolute) | log10 | 10k → 0, 10M → 100 | 0.50 |
| Realized growth | T-100 passengers, trailing 12 months vs prior 12 | linear | −5% → 0, +10% → 100 | 0.30 |
| Market strength | Home-CBSA per-capita income (BEA, latest year) | linear | $45k → 0, $110k → 100 | 0.20 |

* **Flags** are reported, never hidden in the score:
  * `REGULATORY_CAP` (curated, cited);
  * `AIRFIELD_BINDING`: scheduled peak above the verified FAA IMC rate in ≥5% of operating hours;
  * `AIRFIELD_UNKNOWN`: no verified rate;
  * `CARRIER_CONCENTRATION`: largest carrier holds >50% of seats.
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
| Writing the explanation | LLM | Placeholders only, validated. Claims are labelled fact, inference, hypothesis or external. |
| Charts | deterministic | ChartSpec (findings + type + validated title) → Vega-Lite. |
| Memory updates | deterministic + validated tool | State is updated from tool calls. `update_memory` records assumptions and corrections; summaries are number-free. |
| Web context | LLM chooses pages; code verifies quotes | |

## 4. Key trade-offs

* **Deterministic core vs flexibility.** The DSL covers most questions: in the generated evaluation, the failures were step-budget exhaustion, not missing operators. `query_sql` handles the long tail, labelled exploratory. The cost is maintaining the semantic layer, and the benefit is that every number is reproducible.
* **Custom loop vs agent framework.** About 300 lines that we fully control and test with scripted models. We forgo framework conveniences such as built-in tracing UIs.
* **Lexical memory vs embeddings.** References in this domain are codes, names and ids, where exact matching wins. No embedding calls means no cost and no extra service. The upgrade path is SQLite FTS5, then embeddings behind the same `retrieve()` signature.
* **Data freshness vs reproducibility.** Answers carry periods and vintages. A rebuild from the committed raw archive is bit-for-bit identical, and new vintages are additive.
* **Public data limits, stated rather than papered over.** There is no fare, spill or booking data, so unmet demand is inferred, not measured. On-Time is domestic and reporting carriers only, so coverage is shown. TAF is an unconstrained FAA forecast. Terminal capacity (gates, square feet) is not in public structured data; web research can add cited context, but not "facts".
* **Voice.** Browser Web Speech (recognition + synthesis) drives the same agent at zero cost. A real-time voice stack (e.g. Pipecat + WebRTC) is the documented upgrade path ([docs/07](docs/07-product-phase-plan.md)).

## 5. Quality evidence

* **Tests (offline, no model calls):**
  * data pipeline, golden analytics values, typed errors, property tests;
  * regressions from two independent adversarial reviews;
  * memory: a 120-turn budget test and a poisoned summariser;
  * runtime with scripted and mocked-Gemini backends, the API over SSE, web SSRF and quote checks.
* **Reviews** (Grok 4.7, xhigh): data audit (16 findings), engine adversarial review (18), product-layer review. All are logged in [docs/06](docs/06-phase2-audit-review-log.md) and [docs/09](docs/09-product-review-log.md).
* **Agent evaluation:** 70 generated questions. With Grok as the planner the run scored 47/49 before it was stopped, with zero ungrounded numbers by construction ([docs/06](docs/06-phase2-audit-review-log.md)).
