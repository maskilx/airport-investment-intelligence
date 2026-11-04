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

## 2. Adversarial review of the analytics engine (18 findings)

Grok exercised the system only through the tool CLI, and re-derived numbers with independent SQL. Every HIGH
finding was reproduced and fixed, with a regression test (`tests/test_analytics.py`, section "regressions from the
Grok adversarial review").

| Sev | Finding | Fix |
|---|---|---|
| HIGH | `query_sql` whitelist bypass: comma join, `/**/` comment, `information_schema`, `duckdb_tables()`, `sniff_csv`, `current_setting` | whitelist enforced on **DuckDB's own parse tree** (`json_serialize_sql`): only whitelisted base tables; table functions and system/file functions rejected; engine connection runs with `enable_external_access=false`; engine errors become `invalid_spec` |
| HIGH | Annual `offset_months` ignored, so the default change compared a year with itself (0%) | offset applied along the annual calendar; a transform comparing a window with itself is refused |
| HIGH | Transform on a static source (NPIAS) gave a citable "$0", and `estimated` was relabelled `calculated` | `not_applicable` for static sources; transforms keep the weakest input class (hypothesis > exploratory > estimated > forecast) |
| HIGH | Area value (CBSA population) repeated on every breakdown row; `derive` could add it twice | rows carry an explicit "never add across rows" caveat; `derive` refuses sums/differences of area values |
| HIGH | "Dallas" bound to Love Field (DAL) | exact-city match becomes **ambiguous** when a larger airport serves the same CBSA |
| HIGH | CAGR trusted a caller-supplied `years`; unequal windows accepted | years inferred from the resolved windows and printed in the label; unequal-length windows refused |
| HIGH | Grounding: spelled numbers, non-ASCII numerals (½ ² ㊿), finding cited in a sentence about another airport, numeric hypotheses | number words and Unicode numerics rejected; placeholder-vs-sentence airport check; hypotheses may not carry quantities; raw caveat codes mapped to text |
| MED | Two FAA LIDs on one airport summed for TAF/NPIAS | one LID per airport (prefers the airport's own FAA LID) |
| MED | On-Time coverage attached even when filters changed the scope | coverage not attached under filters (note emitted) |
| MED | Stock ÷ multi-year flow (`npias_need_per_enplanement` over a CY range) | refused: a stock metric needs a single-year window |
| MED | `AIRFIELD_BINDING` fired at 0.17% of hours | threshold (5% of operating hours, config) and the share shown with the flag |
| MED | Historical TAF carried the forecast caveat; mixed FY ranges unlabelled | forecast caveat only when forecast; mixed ranges noted |
| MED | Catalog coverage hid the ACAIS gap; `cy`+`fy` window silently used `cy` | annual coverage lists missing years; both calendars rejected |
| MED | Resolver: "National" matched every "Inter**national**"; alias groups without size floor | word-boundary name matching (DCA first); alias groups use the 10k-enplanement floor |
| MED | Multiple T12 windows in one answer; `group_by year` on a partial window | each finding states its own window (note emitted); partial-year caveat added |
| MED | Carrier with T-100 traffic but no On-Time rows shows NULL | kept: NULL is correct (not a reporting carrier); documented |
| LOW | Tool tables rounded to 6 significant figures; annual lineage spanned the whole source | integers printed exactly; annual lineage lists the publications used |
| LOW | `log10(x ≤ 0)` contributes 0 in the screen | by design: the input is the absolute *increase*; a decrease scores 0 on that component (documented) |

The review also verified as correct, against independent SQL:
- seat factor, filtered passengers, long-haul parameters, delay rate, coverage, peak hour;
- distinct-area group totals, rank scores, correlation, anomaly, forecast vs actual;
- screen contributions (to the decimal), and injection-like resolver inputs (returned `unknown`, no error).

## 3. Agent evaluation

Question bank: `eval/questions.jsonl`, 70 questions generated by Gemini *after* the engine was built (not tuned on).
Categories: known 10, unseen 20, multi-step 12, ambiguous 8, unanswerable 10, adversarial 10.

The agent may only use the tool CLI (allow rule = one command). Scoring reads OUR artifacts: the tool-call audit log
and the answer rendered by `compose_answer`, never the agent's own prose.

**Scorer corrections (not agent changes):**
- hub-class enums are compared semantically (`large_hub` ≡ `hub_class "L"`);
- the contract markers `CLARIFICATION:` / `CANNOT_ANSWER:` are detected even after a preamble, and refusals without a marker are judged by meaning;
- a correct clarification needs no analysis op;
- forbidden-claim phrases inside a negation ("fares are not available") are not counted as claims.

### Grok 4.7 (xhigh) as agent — 49 of 70 questions completed, run stopped deliberately
| Category | Pass |
|---|---|
| known | 10/10 |
| unseen | 19/20 |
| multi_step | 12/12 |
| ambiguous | 4/5 |
| unanswerable | 2/2 |
| **total** | **47/49** |

The 2 genuine failures (q019, q049) hit the 40-turn budget. q019 kept retrying `forecast_vs_actual` on historical
FAA TAF years. Fix: the `not_applicable` error now carries a recovery hint. Median 11 tool calls per question.
The 21 questions not run are 1 ambiguous, 8 unanswerable and all 10 adversarial (adversarial behaviour is partly
covered by the Gemini pilot rows q062/q066 and by the adversarial code review).

### Gemini 3.8 Flash via Antigravity CLI (`agy` 1.5.0, account quota, no API) — pilot, 14 questions
**Configuration:**
- Run: `--model gemini-3.8-flash-medium --effort medium --print --output-format json`.
- Model listed by `agy models`. An invalid model id is rejected with an error. The JSON output does **not** echo the model or the effort actually used.
- Tool access: one allow rule, `command(.venv/bin/python -m airport_analytics call)`, verified in our audit log.
- Usage: median latency 74.5 s, median ≈101k tokens per question (input + output + thinking, as reported by `agy`).

**Results:**
- Medium: 3/14 (q016, q043, q066).
- High effort, diagnostic rerun of 6 failures: 0/6.
- Failure mode: the session ends with status SUCCESS and an **empty final response** after a few tool calls, without
  `compose_answer` or a contract marker. Malformed specs were also more frequent than with Grok (e.g. `airports` outside `entities`).

**Conclusion:** in this CLI print-mode harness, Gemini 3.8 Flash does not reliably complete multi-step tool
workflows, so it is not used as the evaluation agent. Grok remains the evaluation agent. Gemini stays in use for
generation and research tasks, where it performed well. This says nothing definitive about Gemini in our own agent
loop: that loop nudges a model that stops without `compose_answer` (tested in `tests/test_agent_loop.py`), and CLI print mode has no such mechanism.

### Tests at the end of the evaluation window
- Full suite: **134 passed** (incl. slow offline rebuild/reproducibility tests).
- After the last code change (the recovery hint): fast suites rerun, 109 passed.
