# Phase 3 — Product Plan: Agent Runtime, Analyst Workspace, Voice, Web Research

Status: **plan for review (no implementation, no new dependencies yet)** · Date: 2026-11-04 · Owner: Claude
Builds on: [04](04-phase2-analytics-plan.md) methodology · [05](05-analytics-architecture.md) engine and tool architecture · [06](06-phase2-audit-review-log.md) audit, review and evaluation log.

Evidence labels:
- **[verified]** = checked by Claude this session (GitHub API or our own runs);
- **[research]** = from the Grok research briefs (cited URLs, read 2026-11-04, not re-opened by Claude);
- **[proposal]** = recommendation.

Raw research: `research/next_phase_taskA.md`, `research/next_phase_taskB.md`.

---

## 1. Executive summary

The hard part is already built and tested: deterministic analytics, typed tools, provenance, and grounding
enforcement. The next phase is mostly integration: put a streaming server and a professional UI around it.
Add voice and web research without weakening the "every number comes from a finding" guarantee.

Decisions:
| Layer | Decision | Why |
|---|---|---|
| Agent runtime | **Keep our thin loop** and add timeouts, turn/tool caps, cancellation, streaming events, and a Gemini API adapter | Frameworks would replace, not extend, the grounding contract. Our loop is about 150 lines and already tested with a scripted backend |
| Backend | **FastAPI + Pydantic v2 + `sse-starlette`**, SQLite for conversations | Same process as DuckDB and the validator; standard, MIT/BSD, $0 |
| Frontend | **Vite + React + TypeScript + assistant-ui**, speaking the **Vercel AI SDK UI-message stream** emitted by our FastAPI | Reuses mature chat UX (threads, tool-call UI, streaming) without Next.js, auth or hosted databases |
| Charts | **Vega-Lite specs built server-side** from a closed `ChartSpec` DTO, validated with JSON Schema, rendered by `vega-embed` | Declarative and schema-validated; the model never emits chart code |
| Voice | **Pipecat + SmallWebRTC** (local, peer-to-peer). The voice pipeline calls **our** agent loop, so there is one brain. faster-whisper STT and local TTS. Hebrew TTS is the open risk | Voice is optional for the assignment; this path is $0 and keeps grounding |
| Web research | New tools `web_search` and `fetch_page` (SearXNG self-hosted, or `ddgs` fallback, plus `trafilatura`), producing **`external_web` evidence** with `{W#}` placeholders, kept apart from findings | Zero-cost, citable, and never mixed with validated internal data |
| Eval/observability | **No new framework**: keep our harness and JSON traces, using OpenTelemetry GenAI attribute names | The harness already checks what matters (grounding, tool trajectories); Langfuse needs four datastores |
| Product LLM | **Decision needed** (§8): the Gemini API free tier (rate-limited; Google may use the data) or a paid key. This is distinct from the Antigravity CLI used for development | No mandatory paid dependency; the evaluation must be re-run through *our* loop before committing to a model |

**Recommended first task:** Stage 1, the hardened streaming agent runtime plus a Gemini API adapter, followed by
the existing 70-question eval run through our own loop (§7).

## 2. What the product must be

An analyst workspace, not a chatbot. The left column is the conversation (text or voice). The right column is the
"evidence workspace": tool-activity timeline, findings and sources table, and charts and tables generated from
structured results. Follow-up questions reuse prior findings (`F#` ids persist per conversation).

Assignment essentials versus extras:
| Requirement | Source | Status after this plan |
|---|---|---|
| Public data, deterministic ranking/KPI, explanations, follow-ups | assignment (explicit) | engine done; follow-ups need conversation state (Stage 2) |
| Chat interface | assignment (explicit) | Stage 3 |
| Design / architecture document (scoring, trade-offs, AI usage) | assignment deliverable | consolidate docs 04–07 into one short document (Stage 8) |
| Voice | assignment "bonus" | Stage 7 (optional) |
| Web research, charts, Hebrew | product vision (this brief) | Stages 5–7 |

## 3. Framework evaluation and decisions

### 3.1 Agent orchestration [research + proposal]
| Option | What it would give us | Cost to us | Verdict |
|---|---|---|---|
| **Custom loop (current)** | Full control of the grounding contract (`compose_answer`, `{F#}`, nudging a model that stops early). Scripted test backend. Anthropic-format transcript | We add timeouts, caps, cancellation and event streaming (about 1 day) | **Use** |
| Pydantic AI (MIT, very frequent releases) | Usage limits, timeouts, cancellation token, event streaming, `TestModel`, provider strings, a Vercel AI adapter | Re-wrap the 7 tools, adopt its message model, its Agent owns the steps and the history, and pin a fast-moving library | Defer; revisit only if the loop grows substantially |
| LangGraph (MIT) | Durable graphs, checkpoints, interrupts | A second state model; LangSmith gravity; the wrong shape for one 7-tool analyst | Reject |
| OpenAI Agents SDK (MIT) | Handoffs, guardrails | Default tracing sends run data to OpenAI; non-OpenAI models via extras | Reject |
| Google ADK (Apache-2.0) | Gemini-first runner, sessions, eval | A large runtime with its own session and eval formats; GCP deployment gravity | Reject |

**Evidence for keeping the loop:** the Antigravity-CLI pilot ([06](06-phase2-audit-review-log.md) §3) showed Gemini
ending tool sessions early with empty output. Our loop already detects and nudges exactly that case
(`tests/test_agent_loop.py`). A framework would have to be configured to do the same, and may hide it.

### 3.2 Backend [research + proposal]
FastAPI (MIT) + Pydantic v2 + `sse-starlette` (BSD-3-Clause), with stdlib `sqlite3` for conversations.

Streaming design, one SSE response per turn:
- events: `tool_started`, `tool_finished` (structured result plus optional chart spec), `status`, and finally `answer`;
- the `answer` is emitted only **after** server-side validation and rendering.

**Model token deltas are not streamed raw.** A streamed digit could reach the user before the validator has
accepted it. Instead, tool events give the UI continuous progress, and the final answer appears all at once (or as a
typewriter replay of the already-validated text).

Cancel on client disconnect, checked between tools. Whether an in-flight DuckDB query can be interrupted is
unverified, so a hard per-query timeout is kept.

Build ourselves: session repository, SSE route, cancellation, event models. Not needed for the demo: auth, Redis,
job queues.

### 3.3 Frontend and chat UX [research + proposal]
| Option | Verdict |
|---|---|
| **assistant-ui** (MIT [verified]) on the **Vercel AI SDK** UI-message stream (`x-vercel-ai-ui-message-stream: v1`: text, tool input/output, `source-url`, `data-*` parts) | **Use**: thread, composer and tool-call UI exist. Our FastAPI emits the protocol; Vercel hosting is not needed. Official FastAPI example: `vercel/ai/examples/next-fastapi` [research; GitHub API rate-limited during verification] |
| vercel/ai-chatbot template | Reject: Next.js + Auth.js + Postgres + Redis + Blob storage, far more than needed |
| CopilotKit (MIT) | Reject: its runtime would sit in front of our agent |
| Chainlit | Reject: **archived** [verified, GitHub API] |
| Open WebUI / LibreChat | Reject: whole applications with their own agents and RAG; Open WebUI has a custom license with branding clauses |
| Streamlit | Reject: weak tool-trace streaming; no workspace layout |

Vercel AI SDK license: research says Apache-2.0, but the GitHub API reports `NOASSERTION`. Confirm from the
LICENSE file before adoption.

**Do not copy** `vercel-labs/ai-sdk-preview-python-streaming`: it uses the old protocol, has no LICENSE file, and depends on the AI Gateway [research].

### 3.4 Visualization [research + proposal]
**Vega-Lite**: Altair (BSD-3-Clause [verified]) builds specs in Python; `vega-embed` renders them. The flow:
1. analytics results carry a closed `ChartSpec` DTO (mark ∈ {bar, line, scatter, heatmap}, fields, rows);
2. Python maps it to Vega-Lite;
3. `jsonschema` validates it;
4. the spec allows only inline `data.values` (no `data.url`, no `calculate` expressions).

Plotly (MIT) is a fine alternative but its specs are looser and larger (≈0.4–1.5 MB gzip) [research].

### 3.5 Real-time voice [research + proposal]
| Option | Fit | Cost / hosting | Verdict |
|---|---|---|---|
| **Pipecat** (BSD-2-Clause [verified]) + **SmallWebRTC** transport | Local peer-to-peer WebRTC, VAD + barge-in, function-calling examples; Python, same process family as our tools | $0 local | **Use for the demo** |
| LiveKit Agents (Apache-2.0 [verified]) + livekit-server | Best turn-taking (trained end-of-turn); production-grade | Self-hosting means a media server + TURN; Cloud free tier 1,000 agent-min [research] | Upgrade path |
| Gemini Live API | Native audio, server VAD, function calling; Hebrew listed in the developer API [research] | Free tier: Google uses prompts to improve products; paid ≈ $0.005/min in, $0.018/min out [research] | Optional Hebrew path, behind a flag. It is a *second brain*: tool results must be pre-rendered and grounded |
| OpenAI Realtime | Strong but paid | ≈ $32/$64 per 1M audio tokens [research, secondary sources] | Reject (cost) |

**One brain for text and voice:** the Pipecat pipeline is VAD → STT → *our `Agent.ask`* → speak. Its LLM step is a
custom processor that calls our loop; Pipecat's own LLM service is not used. So voice answers are the
**same validated, rendered answer**, spoken as a short summary, with full evidence shown on screen. Latency is
higher than native speech-to-speech; acceptable for an analyst demo.

STT: faster-whisper (MIT), which supports Hebrew and English. TTS: English is fine locally (Piper/Kokoro). **Hebrew TTS
is the gap**:
- Kokoro has no Hebrew;
- community Piper Hebrew voices may be non-commercial;
- the maintained Piper successor is GPL-3.0 [research].

Options: English-only voice for the demo, or Gemini Live / a cloud TTS for Hebrew behind an explicit opt-in flag.

### 3.6 External web research [research + proposal]
New tools:
- `web_search(query)`: SearXNG (AGPL-3.0, self-hosted container, no key) with `ddgs` (MIT, best-effort, no SLA) as fallback;
- `fetch_page(url)`: `trafilatura` (Apache-2.0) extraction; returns a quoted passage.

Each result becomes an **`ExternalEvidence`** record:
- fields: url, title, retrieved_at, query, quoted snippet (length-capped), extractor;
- class `external_web`, placeholder `{W#}`;
- the validator treats `{W#}` like `{F#}`, so numbers from web text still need a placeholder;
- the renderer shows web sources in a separate "External sources" section, never inside the internal evidence table;
- web content is never written into the database or used by the scoring model.

Prefer an allow-list of official domains (faa.gov, bts.gov, transtats.bts.gov, airport-authority sites) for
"authoritative" labelling.

Paid or limited options, not in the default design: Tavily (1k credits/month), Exa, Brave (pricing pages conflict),
Gemini Search grounding (5k/month, then $14 per 1k) [research].

### 3.7 Evaluation and observability [research + proposal]
Keep our harness (`eval/run_eval.py`) and add **structured JSON traces** per turn: model id, tool sequence, latency,
tokens, and validator outcome, using OpenTelemetry GenAI attribute names (the spec is still at Development status).
No Langfuse (web + worker + Postgres + ClickHouse + Redis), no Phoenix (Elastic-2.0 license), no DeepEval
(LLM-judge; telemetry on by default) [research].

## 4. Proposed architecture

```
Browser (Vite + React + assistant-ui + vega-embed)
  │  HTTP POST /chat  ──►  SSE: tool_started / tool_finished(+chart) / status / answer
  │  WebRTC (voice, optional) ──► Pipecat pipeline (VAD → faster-whisper → AgentProcessor → TTS)
  ▼
FastAPI app (airport_api)                                    [new]
  ├─ ConversationStore (SQLite: turns, finding ids, traces)  [new]
  ├─ TurnRunner: Agent.ask(...) as async task, cancel, timeouts, event callback   [extends airport_agent]
  │     ModelBackend adapters: Gemini API | Anthropic | Scripted(test)            [Gemini new]
  ├─ Tools (unchanged contract) ── airport_analytics (engine, evidence, render)  [existing]
  │     + web_search / fetch_page → ExternalEvidence store                        [new]
  │     + ChartSpec → Vega-Lite builder + JSON-schema validation                  [new]
  └─ airport_data DuckDB (read-only)                                              [existing]
```

**Interface changes needed before integration:**
1. `Agent.ask` gains an event callback, cancellation flag, wall-clock and turn budgets, and async execution.
2. The `EvidenceStore` is persisted per conversation (today a pickle in the CLI), so follow-ups resolve earlier `F#` ids.
3. Analysis results expose an optional `chart` (`ChartSpec`).
4. `render()` returns structured parts (headline, body, claims, evidence rows, sources) besides markdown, so the UI renders panels, not a markdown blob.

## 5. Technology stack, licences and cost
| Component | Licence | Cost model |
|---|---|---|
| Python, DuckDB, FastAPI, Pydantic, sse-starlette, Altair, jsonschema, trafilatura, ddgs, faster-whisper, Pipecat | MIT / BSD / Apache | free, local |
| SearXNG | AGPL-3.0 | free; self-hosted container (local CPU and RAM only) |
| React, Vite, TypeScript, assistant-ui, vega-embed | MIT / BSD | free, local |
| Vercel AI SDK (client parts) | Apache-2.0 per research; GitHub `NOASSERTION` → confirm | free library |
| LLM for the product | — | **the only potentially paid item.** Gemini API free tier (rate-limited; data may be used by Google) or a paid Anthropic/Gemini key. No automatic paid fallback |
| Gemini Live (optional Hebrew voice) | proprietary | free tier with data-use terms; paid beyond |
| Hosting | — | none required (local demo). Any deployment is extra and out of scope |

## 6. Roadmap
Effort estimates assume the current codebase; priority **P0** = needed for the assignment demo, **P1** = strong value, **P2** = optional.

| # | Stage | Objectives & deliverables | Reuse / new | Depends | Risks | Acceptance & tests | Effort · Prio |
|---|---|---|---|---|---|---|---|
| 1 | **Runtime hardening + product LLM** | async `Agent` with event callback, cancellation, wall-clock/turn/tool budgets; `GeminiBackend` (google-genai SDK, Messages↔Gemini mapping); JSON traces | reuse loop, scripted backend; new adapter | — | free-tier rate limits; tool-call schema mapping | unit tests (scripted); **70-question eval through our loop** with the chosen model; ≥ Grok-CLI baseline on known/unseen/multi-step; 0 ungrounded numbers | 1 d · P0 |
| 2 | **API + conversation state** | FastAPI `/chat` SSE, `/conversations`, SQLite store, persisted EvidenceStore, follow-ups | reuse tools, render; new api package | 1 | SSE + cancellation edge cases | httpx tests: stream order, disconnect cancels, follow-up cites earlier `F#` | 1 d · P0 |
| 3 | **Text workspace UI** | Vite+React+assistant-ui chat; tool-activity timeline; evidence and caveat panel from structured render parts | reuse assistant-ui, AI SDK protocol; new panels | 2 | protocol version drift | Playwright smoke: ask, stream, evidence panel, follow-up | 1.5 d · P0 |
| 4 | **Structured visualizations** | `ChartSpec` on rank/trend/compare/correlate results; Vega-Lite builder; JSON-schema validation; render in workspace | Altair, vega-embed; new builder | 2–3 | spec injection (`url`/`calculate`) | schema tests, rejection tests, snapshot of 4 chart types | 0.5–1 d · P1 |
| 5 | **Architecture document + demo script** | one short doc: scoring methodology, trade-offs, AI usage (assignment deliverable); demo walkthrough of the 4 questions plus unscripted ones | consolidate docs 04–07 | 1–3 | — | reviewed doc; demo dry run | 0.5 d · **P0** |
| 6 | **External web research** | `web_search` / `fetch_page`, ExternalEvidence `{W#}`, domain allow-list, separate sources section | SearXNG / ddgs, trafilatura; new tools | 2 | rate limits, page quality, prompt injection from web text (treat as data) | grounding tests for `{W#}`; injection test; eval items needing web context | 1 d · P1 |
| 7 | **Real-time voice** | Pipecat + SmallWebRTC; AgentProcessor calling our loop; English TTS; Hebrew via opt-in provider | Pipecat examples (function calling, SmallWebRTC); new processor | 1–2 | latency; Hebrew TTS quality and licensing; echo/barge-in | manual latency test; spoken answer equals the rendered answer's summary; interruption cancels the turn | 1–1.5 d · P2 |
| 8 | **End-to-end evaluation & final demo** | re-run the full eval (incl. adversarial items) through the API; latency/cost report; final polish | harness | all | — | report committed; all tests green; offline rebuild passes | 0.5 d · P0 |

Sequence note: Stage 5 (the architecture document) moves ahead of the optional features because it is an explicit
assignment deliverable.

## 7. Recommended first implementation task
**Stage 1:**
1. Make `airport_agent.Agent` async with an event callback, cancellation and budgets.
2. Add `GeminiBackend` (official `google-genai` SDK, free-tier API key supplied by you; no paid fallback).
3. Write JSON traces.
4. Re-run the 70-question evaluation through **our** loop, not a CLI.

Done when:
- the scripted tests pass;
- the eval meets the Grok-CLI baseline on known, unseen and multi-step;
- every rendered number traces to a finding.

This removes the main open uncertainty: whether the product model completes tool workflows inside our loop.

## 8. Risks, trade-offs and deferred items
| Item | Note |
|---|---|
| Product model choice | The free Gemini API tier has rate limits and data-use terms; Anthropic requires a paid key. **Your decision.** Gemini in our loop is not yet evaluated (the CLI pilot failed for harness reasons, see 06 §3) |
| Streaming vs grounding | Raw token streaming is intentionally not shown; progress comes from tool events |
| Hebrew voice | No good free local Hebrew TTS identified; English voice for the demo, Hebrew opt-in |
| Second brain risk | Native speech-to-speech models (Gemini Live) could speak ungrounded numbers. Allowed only to read already-rendered answers |
| Web prompt injection | Fetched text is data. It is quoted, never followed, and never written into findings |
| Repo size | 436 MB pack (raw data); move raw data to Git LFS before publishing |
| Deferred | DB1C fares/O&D, terminal-capacity verification, multi-user auth, cloud deployment, LiveKit upgrade |

## 9. Sources
Research briefs with full URL lists: `research/next_phase_taskA.md` (orchestration, backend, charts, observability),
`research/next_phase_taskB.md` (chat UI, voice, web research). Key repositories:
- [assistant-ui](https://github.com/assistant-ui/assistant-ui) · [vercel/ai](https://github.com/vercel/ai) (stream protocol: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol)
- [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) · [livekit/agents](https://github.com/livekit/agents) · [google-gemini/live-api-web-console](https://github.com/google-gemini/live-api-web-console)
- [vega/altair](https://github.com/vega/altair) · [searxng/searxng](https://github.com/searxng/searxng) · [adbar/trafilatura](https://github.com/adbar/trafilatura) · [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- Gemini pricing (incl. Live, grounding): https://ai.google.dev/gemini-api/docs/pricing
