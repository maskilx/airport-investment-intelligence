# Assignment compliance and submission readiness (strict review, 2026-11-04)

Each row was verified on the running application unless it says otherwise. Browser checks used the offline planner
on a separate instance (port 8766, a copy of the conversation store) to avoid spending any LLM quota. "Offline" means
the deterministic rule-based planner; **the live LLM path (Gemini or Groq) has not completed a successful run** (see
"Live AI" below).

## Compliance matrix

| Requirement | Status | Where (code) | Proof (test / demo) | What the user sees | Limitation an interviewer may raise |
|---|---|---|---|---|---|
| Q1: New England terminal-expansion candidates | **PASS** | `screening.py`, `config/screening.toml`, `claims.py` | `test_screen_answer_explains_score_composition_and_method`; browser | Deterministic ranking; per-airport `score = Σ contributions` (clickable); "How the score is calculated"; ranking robustness; stage-A framing ("not a terminal-need assessment") | Measures passenger-growth opportunity, not terminal suitability (stage B is not built). All flags `AIRFIELD_UNKNOWN` outside SFO. |
| Q2: LA vs Santa Ana congestion | **PASS** | `offline.py`, `claims.py` (comparison checks) | `test_comparison_direction_compatibility_and_periods_are_checked_by_code`; browser | Same-window comparison per indicator; delay rates "similar (within 5%)"; taxi-out and peak hour higher at LAX; note that these are airside, not terminal crowding; window differences disclosed | On-Time covers reporting carriers on domestic flights only (coverage shown). Windows differ between sources (disclosed). |
| Q3: ANC long-haul percentage | **PASS** | `semantic.py` (`long_haul_share` params), `assumptions.py` | `test_offline_threshold_follow_up_binds_and_reruns`; browser | Threshold and denominator explicit in each label (`min_miles=3000, weight=departures` → 4.4%; passengers → 6.1%; 2,400 mi → 13.6%). "Use 2000 miles instead" re-runs (16.4% / 30.3%) and stales the old findings | Segment distance, not true origin-destination trip length. |
| Q4: SFO unmet demand and why | **PASS** | `information.py`, `offline.py`, `claims.py` (hypothesis rules) | `test_reviewer_counterexample_*`; browser | **No unmet-demand number.** Demand-pressure indicators, a labelled hypothesis with three competing explanations, an investigation summary (unknown: denied demand; next step: fares from the Origin and Destination Survey, capacity profile) | Indicators, not measurement, by design. |
| Use public APIs to gather data | **PARTIAL (honestly scoped)** | `airport_data/sources/*`, `live_status.py` | `test_live_faa_status_is_external_evidence_with_verbatim_quotes`; link audit | Inspector shows publisher, dataset page and exact raw file or form for every value; live FAA status is cited as external evidence | Historical data comes from automated public **file downloads and reporting forms**, not REST APIs. One real public REST API (FAA NAS Status, live) was added. See ARCHITECTURE §1b. |
| Rank or compare by defined logic / KPI | **PASS** | `screening.py`, `analysis.py` (rank), `claims.py` | screen, rank and comparison tests | Documented weights, anchors, gate and ties; comparisons with code-checked direction | Weights are analyst assumptions, not fitted to returns (stated). |
| Explain reasoning clearly | **PASS (offline) / NOT VERIFIED (LLM)** | `render.py`, `claims.py`, UI | browser | Answer, then investigation summary, evidence (measured or calculated), interpretation and judgment, assumptions, limitations, method; tooltips on every tag | LLM-written explanations have not had a successful live run. |
| Conversational follow-ups | **PASS** | `memory.py`, `offline.py` | `test_decision_uses_conversation_context_before_asking`, `test_changing_the_objective_changes_the_criteria`, voice follow-up test; browser | "the third one", "their trend", "its seat factor", threshold change, objective change, ambiguity ("Portland"), proceeding on a stated assumption, a clarification when the objective changes the answer | The offline planner understands a fixed set of intents. |
| Deterministic scoring (not only LLM) | **PASS** | `screening.py`, `analysis.py` | `test_screen_is_additive_and_never_imputes`, replay tests | Contributions sum to the score; replay reports match / build / config | n/a |
| Chat interface | **PASS** | `web/`, `airport_app/server.py` | API and browser tests | Streaming answers, charts, evidence inspector, conversation list, restart persistence | Local web app (no deployment). |
| Voice (bonus) | **PARTIAL** | `voice.py`, `web/app.js` | `test_spoken_question_runs_the_same_agent_with_follow_up_context`, browser hook tests | Live voice bar: listening, processing, speaking; transcripts; barge-in; recovery; same conversation | **Real microphone and audible output not tested here** (no audio device in the test browser); server STT needs your Groq key. |
| Assumptions, uncertainty and scoping | **PASS** | `claims.py`, `information.py`, assessments | trust tests | Assumptions and limitations sections, abstentions with reasons, computed sensitivity, proxy labels, stale-finding enforcement | n/a |
| Deliverable: source code | **PASS** | GitHub `maskilx/airport-investment-intelligence`, branch `trust-architecture` | push verified | n/a | n/a |
| Deliverable: design document (scoring, trade-offs, AI use) | **PASS** | `ARCHITECTURE.md` (+ docs/10, voice and provider reviews) | n/a | n/a | Long for "short"; §2 to §4 are the interviewer's core. |
| Live AI (the agent with a real LLM) | **NOT VERIFIED** | `models.py` (Gemini, Groq) | Fake-endpoint tests for both adapters (`test_groq_adapter_runs_the_same_agent_end_to_end`, Gemini tests) | Header badge shows provider, model and usage | The only live attempt (Gemini, one request) got **HTTP 503 provider overload** and was not retried; Groq needs your key. |

## FDE-style behaviour (demonstrated in the browser, offline planner)

| Situation | Behaviour |
|---|---|
| Data missing (airfares at AUS) | Classified "external"; proxies run and labelled ("Proxy, AUS: Seat factor…"); what cannot be established; next step: add the BTS average-fare dataset |
| Cannot be measured (SFO unmet demand) | Indicators, hypothesis with alternatives, investigation summary, next step |
| Objective resolvable from context ("Which one should we prioritize?" after a screen) | Proceeds; states "Assumed from context: options BOS and PWM; objective passenger growth opportunity" |
| Objective materially ambiguous ("Which is better, LAX or SNA?") | One focused question: growth opportunity or airside congestion? |
| Decision with conflicting criteria | Trade-offs stated; sensitivity computed from documented scenarios; abstains when too close (PVD vs BDL) |

## Submission readiness

**Decision: READY WITH EXPLICIT LIMITATIONS.**
* **Code and design document:** ready.
* **Offline demonstration:** ready. The four questions, decisions, missing-information handling, evidence inspection and follow-ups were all exercised in the real UI.
* **Not yet ready:** the AI-agent demonstration with a live LLM, which has not completed a successful run.

Remaining issues, in priority order:
1. **One successful live LLM run.**
   * Gemini: the single smoke request hit a provider 503. You have 24/25 daily requests and 4 smoke requests left.
   * Or Groq: enter the key, then run the 5-request smoke test.
   * Do this before the interview.
2. **Real-microphone voice check** in Chrome or Safari. For server STT, set `AIRPORT_VOICE_STT=groq` after the Groq key is set up.
3. **Groq free tier is slow** for this agent (8k tokens per minute means pacing). Decide on the Developer plan (about a cent per question) if Groq is the demo provider.
4. **Eight curated constraint sources are dead or blocked** (marked in the product). Collect primary documents if those constraints are discussed.
5. Stage B terminal suitability and stage C economics are documented next steps, not built.
