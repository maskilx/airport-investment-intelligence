# 10 — Consolidated architecture assessment (handover review)

Scope: reconcile the two independent reviews (Grok 4.7 data/engine/product audits; the second agent's product and
architecture assessment) against the code at `e205c3e`. This document also sets the order of the P0/P1 work on
branch `trust-architecture`.
Every status below was checked against source. A test or a commit message was not taken as proof on its own.

## 0. Snapshot facts (verified)

| Fact | Evidence |
|---|---|
| HEAD `e205c3e`; 18 commits; working tree clean at takeover | `git log` |
| Baseline suite: **186 passed**, offline, 3m41s | `pytest -q` |
| The built DB said `build_info.git_rev = 9edddf2`, built 13:44Z. That is **before** the data-audit fix commit `15ce6a3`, which changes `derived.sql`, `bts.py`, `geo_econ.py` and `atads.py`. | `SELECT * FROM build_info` |
| I rebuilt the DB from the committed archive at `e205c3e` and compared both ways with `EXCEPT ALL`. `dim_airport`, `dim_airport_faa`, `xref_airport_county`, `v_airport_area_econ`, `npias_airport` and `v_faa_grant` are **identical row for row** to the old DB. So the old DB already contained the audit fixes. It was built from an uncommitted working tree and stamped with the HEAD of that moment. **The data was correct; the provenance stamp was wrong.** Fixed: `build_info.git_rev` now ends in `-dirty` when the build code or its inputs differ from HEAD. | rebuild and diff (stage 0) |
| Consequence: review 2's "earlier build 9edddf2" was very likely this **DB build stamp**, not the code revision. HEAD also has 186 tests, and the runtime, memory and API tests it reports were added after `9edddf2`. Treat review 2 as describing code close to HEAD. | test count at HEAD; commit dates |

## 1. Reconciliation of review findings

Status values:
* **fixed**: verified in code at HEAD.
* **open**: reproduced or confirmed by reading the code at HEAD.
* **invalidated**: no longer applies.
* **investigate**: not yet settled.

### 1.1 Grok data audit (16) and engine adversarial review (18)
All 34 are recorded in [docs/06](06-phase2-audit-review-log.md) as fixed or deliberately retained. The fixes have
regression tests (`test_analytics.py`, `test_seed_integration.py`), and spot checks of the SQL whitelist, transform offsets,
static-source transforms, area-value aggregation, the Dallas ambiguity and CAGR window inference match the code.
The live database contains these fixes (verified by rebuild and diff, §0).

### 1.2 Grok product-layer review (19, `docs/reviews/grok-product-review-2026-11-04.md`)
| # | topic | status at HEAD |
|---|---|---|
| 1–4, 16 | numeral allowlist, SQL alias labels, quote boundaries, web titles, ordinals | fixed (`e205c3e`) |
| 5 | free-text assumptions and preferences replayed into context unchecked | open |
| 6 | extractive summary masks digits but not number words | open (`memory.py extractive_summary`) |
| 7 | unpaired `tool_use` (compose not last; `duckdb.Error` escapes `Session.call`) | open |
| 8 | context budget not hard; tool-call cap only checked between steps | open |
| 9 | group keys and retrieved questions carry raw numbers into the memory block | open |
| 10 | web fetch keeps the default `ProxyHandler`, so a proxy bypasses the peer-address SSRF check | open (`web.py:105`) |
| 11 | chart axis titles use raw units (`0-100`) | open |
| 12 | Gemini model id not allowlisted; request budget per process and unlocked | open |
| 13 | provider and driver error text shown to the user | open |
| 14 | `tool_finished.result` streams raw tool JSON (web excerpts) to the UI | open |
| 15 | one cancel slot per conversation; cancel only polled between steps | open (`server.py`) |
| 17–19 | shared DuckDB connection across threads; error-body logging; href scheme | investigate / low |

### 1.3 Second independent review (product and architecture)
| Finding | Status at HEAD | Evidence |
|---|---|---|
| Score measures growth opportunity, not terminal need or return; the "profitable expansion" framing overclaims | **open** | `screening.toml` says *"ranks where the profit pool … is largest"*; finding label "Expansion screen score"; headline "Terminal-expansion screening candidates" |
| Validator accepts "SFO expansion is guaranteed profitable" citing a seat-factor finding | **open** | `render.validate` checks numerals and ids only; any non-empty `support` satisfies a `fact` |
| "Additional gates in 2035" passes because the year is allow-listed | **open** | `ALLOW` admits any 1990–2069 year in any text |
| Body text outside any claim structure | **open** | `body` is validated lexically only |
| Assumption changes do not invalidate findings | **open** | assumptions are free text; `Finding` has no dependency field; `save_findings` uses `INSERT OR IGNORE`, so a later status change would never persist |
| Comparisons do not check metric, period or class compatibility | **open** | `derive` checks units only; claims are not checked at all |
| Replay is not faithful | **open** | `get_finding(reproduce)` re-runs `dict(spec, op="aggregate")`. Screen scores have no spec. No build fingerprint, config hash or resolved entity set is recorded. |
| Constraints: expired caps combined with current ones; capacity parsed from free text; `verified:search_snippet` counted as verified | **open** | `screening.py`: caps query has no date filter; `_verified_imc_rates` applies a regex to `value`; `verification LIKE 'verified:%'` |
| Limits only between iterations; SQL row cap is not a time cap | **open** | `runtime.py` loop head; `tools._sql` `LIMIT 201` |
| Cancellation leaves unmatched tool calls; concurrent turns overwrite the cancel event | **open** | as Grok #7 and #15 |
| Invalid model config silently selects offline | **open** | `backend_from_env`: unknown `AIRPORT_MODEL` falls back to offline |
| Live Gemini through *our* loop not demonstrated | **open** (by design until offline is stable) | only the `agy` CLI pilot exists |
| Voice is browser Web Speech only | true; P2 | |
| Archive ~1.38 GB with dev artefacts | partly by design | the git pack is ~436 MB because raw source vintages are the reproducible seed; `.venv`, the built DB and `data/app` are ignored |

### 1.4 Conflicts between the documentation and the code
1. ARCHITECTURE.md calls grounding *"a guarantee instead of a prompt instruction"*. It guarantees **traceability of numerals**. It does not guarantee semantic validity. The document overstated it.
2. ARCHITECTURE.md and the README describe "17 sources" as if they were public data feeds. Several are files, reporting-form integrations or curated references.
3. The README links `docs/09-product-review-log.md`, which does not exist. The review is at `docs/reviews/`.
4. The eval result (47/49) used Grok through its CLI as the planner. It is not evidence for the product loop with Gemini.

## 2. Architecture assessment

The core design is sound and should be kept:
* immutable vintaged data;
* a semantic layer that owns formulas;
* findings as the unit of numeric truth;
* a small custom agent loop;
* number-free summaries;
* a separate W# evidence path.

The gap is that **the trust boundary stops at "this numeral came from a finding."** Three things sit above that
boundary and are currently unguarded:

1. **Claim semantics.** Whether the cited evidence supports the *kind* of statement made: relation, rank, cause,
   money, capacity need.
2. **Evidence currency.** Whether a finding still holds under the conversation's current assumptions, and whether it
   can be re-derived from what it records.
3. **Investment scope.** Whether "growth opportunity" is being presented as "terminal need" or "return".

The fix is structural, not prompt-level. Deterministic code takes ownership of:
* relations between findings: comparisons and rankings are *rendered by code from finding values*;
* evidence status: current or stale, with the reason;
* the vocabulary that requires stronger evidence classes.

## 3. Design decisions for this branch

| Decision | Alternatives considered | Why |
|---|---|---|
| **Typed claims**: `fact`, `comparison`, `ranking`, `inference`, `hypothesis`, `financial`, `external`. Comparisons and rankings carry structured fields (`findings`, `relation`) that code checks against the values and then renders as a sentence. | (a) Parse free prose with an LLM judge. (b) Keep free prose with a bigger lexicon. | (a) A second model is not a guarantee, and it costs money. (b) It cannot verify direction ("higher" vs "lower"). Typed fields make the relation checkable; the model chooses *what* to claim, and code decides *whether it holds*. |
| **Vocabulary gates** on headline, body and claims. Certainty words are banned everywhere. Financial, causal, capacity-need and judgement language is allowed only in claim kinds whose evidence requirements can be met. Financial or capacity terms in limitations and assumptions need a negation or insufficiency marker. | Ban the words everywhere. | A lexicon is heuristic: paraphrase can evade it. It is defence in depth around the structural checks, not the guarantee. Residual risk is documented. |
| **Years in prose** must appear in the windows, labels or source periods of findings cited in the same answer. | Keep the blanket year allowlist. | Closes the "gates in 2035" hole without banning legitimate period references. |
| **`financial` claims** require findings of class `financial_model`. None exist, so any financial claim is rejected with an instruction to state it as not established, or to ask for analyst assumptions. | Allow hedged financial prose. | This is stage C of the three-stage methodology. Until a conditional economics model with analyst inputs exists, the honest output is "not established". |
| **Execution envelopes** on every finding: tool, op, full original spec, resolved airport ids, catalog version, screening config hash and scenario, data build fingerprint. `get_finding(reproduce)` replays the original op in a scratch store and reports `match`, `build_same`, `entity_set_same` and `config_same`. | Store only the partial spec (status quo). | A rank or screen cannot be reproduced by an aggregate. |
| **Assumption dependencies.** A finding records the active A# ids at creation. An assumption may declare a structured binding (`{metric, param, value}` or `{screen_option, value}`). On supersede or retract, findings bound to that parameter with a different value, or created under an unbound assumption, become **stale**. Stale findings can be inspected but not cited, and the memory index marks them. | Mark everything stale on any change; or nothing (status quo). | Structured bindings are precise. Unstructured assumptions fall back to "created under it", which over-invalidates. That is safe, and the cost is a re-run. |
| **No new frameworks, services, vector store or second agent.** | — | Every guarantee above is a few hundred lines of deterministic code, tested offline. |

## 4. Prioritised plan

**P0: trust and correctness (this branch, one commit per stage)**
0. Rebuild the DB from the committed archive and diff it against the DB being served (done: identical). Stamp dirty builds.
1. Execution envelopes and faithful replay.
2. Assumption dependencies and stale findings (persisted status; validator, context and UI respect it).
3. Typed claim validation and deterministic relation rendering. Offline planner migrated.
4. Runtime hardening:
   * every `tool_use` paired;
   * engine errors contained;
   * tool-call cap inside the step;
   * per-turn cancel events;
   * SQL statement time limit (interrupt);
   * proxy-free fetch;
   * number-word masking in summaries and memory text;
   * explicit failure on an unknown model config.
5. Constraint records: effective-date filtering, a verification ladder (`primary`, `secondary`, `snippet`, `unverified`, `superseded`), and only `primary` or `secondary` used for flags. Free-text capacity parsing removed in favour of structured numeric columns.

**P1: investment reasoning**
1. Rename the score to **Passenger Growth Opportunity Screen (stage A)** across config, labels, UI and docs.
2. Stage B: an intervention-suitability assessment that returns one of `terminal_supported`, `airfield_or_regulatory_dominates`, `committed_project_addresses`, `insufficient_evidence`, from dated, verified constraint and project records. It never infers this from load factor or delay.
3. A small set of primary-source terminal and capacity documents for the demo airports.
4. Stage C only with credible capacity and analyst financial inputs: `incremental_passengers[t] = max(0, min(D,K_project) − min(D,K_base))`. Otherwise it returns break-even or insufficiency.

**P1: integrated validation**
1. Offline end-to-end tests through the API: history, restart, stale findings, charts, cancel, long conversation.
2. Only then, with the user's explicit authorisation, a live Gemini sanity check with a strict request budget (≤ 25 requests).

**P2:** voice, more data, auth, deployment.

## 5. What this branch does *not* establish
* That Gemini plans well through this loop. That needs the budgeted live check.
* Profitability or terminal need for any airport. The data supports a growth-opportunity screen and airside indicators.
* That the vocabulary gates catch every paraphrase. They don't. The structural checks (relations, ranks, staleness, classes) are the guarantee.

## 6. Resolution on branch `trust-architecture`

| Stage | Commit | Closes | Tests (`tests/test_trust.py` unless noted) |
|---|---|---|---|
| 0 | `f72f048` | Build-stamp provenance gap (`-dirty`); rebuild-and-diff showed the data fixes were live | manual rebuild + `EXCEPT ALL` diff (§0) |
| 1 | `f72f048` | Review 2 §6.3: execution envelopes, faithful replay of rank, screen, derive and sql | `test_screen_score_replays_as_screen_not_aggregate`, `test_replay_detects_a_changed_value`, … |
| 2 | `ffa2a81` | Review 2 §6.1; Grok #5 and #6: bound and unbound assumption dependencies, stale findings not citable, persisted status, number-free memory text | `test_bound_assumption_makes_default_threshold_findings_stale_and_uncitable`, `test_offline_threshold_follow_up_binds_and_reruns`, … |
| 3 | `756fd36` | Review 2 §5 and §6.2: typed claims, relations and ranks written by code, compatibility and period checks, financial and capacity-need gating, year provenance | `test_reviewer_counterexample_*`, `test_comparison_direction_compatibility_and_periods_are_checked_by_code`, … |
| 4 | `5d886f0` | Review 2 §6.5; Grok #7, #8, #10–#15: paired tool results, in-flight interrupt (timeout and cancel), per-turn cancel events, hard context cap, explicit model-config failure, Flash-only unless paid is allowed, persisted daily budget, proxy-free fetch, number-free user errors | `test_every_tool_use_is_paired_*`, `test_cancel_interrupts_an_in_flight_query`, `test_hard_context_budget_*`, … |
| 5 | (this commit) | Review 2 §4.1, §4.2 and §6.4: stage A naming and framing; constraint evidence ladder, as-of effectiveness (recorded for replay), strict numeric capacity values, unverified records shown rather than used | `test_constraints_respect_effective_dates_and_evidence_levels`, `test_strict_numeric_parsing_*`, `test_screen_is_framed_as_stage_a_*` |

### Still open (in priority order)
1. **Constraint data schema.** Effectiveness and evidence level are now enforced in code. The CSV should still be migrated to explicit columns: `value_low`, `value_high`, `conditions`, `configuration`, `evidence_level`, `evidence_location`. The migration goes through a new curated vintage. Most terminal and project rows are `unverified:gemini_research` and need primary documents (P1.3).
2. **Stage B assessment.** Build the intervention-suitability assessment (`terminal_supported | airfield_or_regulatory_dominates | committed_project_addresses | insufficient_evidence`) on those records. Today every airport would honestly return `insufficient_evidence`.
3. **API-level end-to-end tests.** Cover two concurrent turns plus cancel, restart mid-conversation with stale findings, and a 50-turn conversation through SSE. The runtime pieces are unit-tested; the HTTP path for these cases is not.
4. **Grok #9.** Retrieved earlier questions and group-filter keys still enter the memory block unmasked. The offline planner parses the group key, so masking needs a structured channel first. Risk is low because the validator rejects any literal in an answer.
5. **Grok #17–#19 (low).** The provenance cursor is shared across request threads (add a lock). Usage-log error bodies need a redaction pass. Restrict the href scheme in the UI.
6. **Eval harness.** Update the scorer for typed claims. Rerun the unrun 21 questions offline-scripted first, then a ≤ 25-request live Gemini sanity check **only with explicit authorisation**.
7. **Stage C economics.** Do not start until stage B evidence and analyst financial inputs exist.
