I'll verify current licenses, release dates, and streaming/tooling fit for the four stack choices, then recommend one option in each area.Licenses and release lines are recent enough that I need the official files, not summaries. I'll open those next.Keep the custom agent loop, serve it with FastAPI and `sse-starlette` over SQLite, render charts as Vega-Lite specs, and add no observability product. Versions below were read from PyPI, npm, or the linked doc on 2026-11-04.

## 1. Agent orchestration

Pydantic AI would replace the loop. It is not a provider shim you can slide under the Anthropic Messages transcript you already have.

| Option | Fit | Complexity | Lock-in | Streaming | Testing | License, last release | Cost |
|---|---|---|---|---|---|---|---|
| Custom loop | Owns tools, `{F#}` grounding, scripted backend, 70-question harness | ~150 lines; you still add timeout, turn cap, cancel | Your message format | You define the events | Scripted model already is the fake | Your code | $0 |
| Pydantic AI | Native `anthropic:` and `google:` strings, `UsageLimits`, `timeout=`, `CancellationToken`, `run_stream_events` | `Agent` owns steps, history, retries. 2.66.0 shipped 2026-11-04 after 2.65.0 (11-03) and 2.64.0 (10-30) | `ModelMessage`, Agent API. Logfire is the documented UI; export is OpenTelemetry | Context-manager stream; leaving it cancels the local task. Google page: closing the iterator does not guarantee remote generation stops | `TestModel` / `FunctionModel` ([testing](https://ai.pydantic.dev/testing/)) | MIT, [LICENSE](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE), PyPI 2.66.0, Python ≥3.11 | $0 library. Logfire and AI Gateway optional |
| LangGraph | Durable graph, checkpoints, interrupts. Wrong shape for one 7-tool analyst | `langchain-core`, checkpoint, prebuilt, sdk (PyPI `requires_dist`) | Graph state. README points at LangSmith | Graph stream / SSE via the SDK | Mock a model inside the graph | MIT, PyPI 1.2.19 (2026-10-30) | $0 library. LangSmith paid |
| OpenAI Agents SDK | Handoffs, guardrails, sessions. Other models only through `any-llm` or `litellm` extras. Hard dep `openai>=3` | Another runner plus their session store | Traces export to OpenAI unless disabled. README: PRs from non-collaborators are not accepted | Run events; voice pipeline is theirs | First-party fake model: UNVERIFIED (testing page not opened) | MIT, PyPI 0.24.0 (2026-10-15) | $0 library. Default tracing sends run data to OpenAI ([tracing](https://openai.github.io/openai-agents-python/tracing/)) |
| Google ADK | Gemini-first runner, sessions, `adk eval`, Cloud Run. README says model-agnostic; `anthropic` is an extra | Large runtime that already depends on FastAPI, `google-genai`, OpenTelemetry | Session and eval formats; deploy docs lead to Cloud Run / Vertex | ADK event stream | Second harness beside yours | Apache-2.0 per the PyPI README, 2.13.0 (2026-10-23), Python ≥3.11. Raw LICENSE file not opened | $0 library. GCP is the gravity |

**Recommendation: keep the loop.** Add three things inside it: a per-request timeout, a cap on model turns and tool calls, and a cancellation flag checked between tools. Keep two adapters (Anthropic SDK, Google GenAI) behind your existing message format, and keep the scripted backend as the test double. Pydantic AI’s real additions are limits, cancel, the event stream, and `TestModel`. Taking them means re-wrapping all seven JSON-schema tools, abandoning the Anthropic Messages transcript, and pinning a library that releases several times a week. Google streaming cancellation still does not promise an immediate end to billed generation ([Google model notes](https://pydantic.dev/docs/ai/models/google/)). Revisit Pydantic AI only if this loop grows a second time. LangGraph, the Agents SDK, and ADK each bring a second state model and a vendor console.

## 2. Backend

| Option | Fit | Complexity | Lock-in | Streaming | Testing | License, last release | Cost |
|---|---|---|---|---|---|---|---|
| FastAPI + Pydantic v2 + sse-starlette | Same process as DuckDB and the validator | Small | HTTP and Pydantic models you already speak | `EventSourceResponse`, ping, `request.is_disconnected()`, `CancelledError` | httpx + the scripted model | FastAPI 0.162.0 (2026-10-23) MIT. sse-starlette 3.6.0 (2026-10-25) BSD-3-Clause, Python ≥3.11 | $0 |
| Starlette alone | Possible | You rebuild request models FastAPI already wires | Low | You write SSE framing | Same | Starlette is FastAPI’s base. Version UNVERIFIED this pass | $0 |
| Django | Poor next to an in-process DuckDB engine | ORM, auth, channels | High | Extra machinery | Heavy | UNVERIFIED this pass | $0 |
| Node/Hono beside Python | Splits the engine from the API | Two processes | A second stack | Fine | Two test suites | UNVERIFIED this pass | $0 |

**Recommendation: FastAPI + sse-starlette + one SQLite file** (stdlib `sqlite3`, beside the DuckDB file, WAL). Litestar is a FastAPI peer; its current release was not checked, and it adds nothing once `sse-starlette` is on the table.

Build the session repository, the SSE route, task cancellation, and the grounding gate. Use FastAPI, Pydantic event models, `sse-starlette`, and the engine you have. Skip auth, Redis, and a job queue for the local demo.

One SSE response per turn, events `tool_started`, `tool_finished` (structured result, optional chart spec), and `status`. Buffer model text. Run the grounding validator. Emit a single `answer` event whose numbers, evidence rows, and chart specs were produced on the server. Forwarding token deltas can emit a digit the validator has not accepted. Tool events are the slow part, so the UI still moves. A typewriter, if you want one, replays that already-rendered string. On disconnect, cancel the task. Cancel between tools. Whether an in-flight DuckDB query can be interrupted is UNVERIFIED.

## 3. Charts from structured tool results

The model never emits JavaScript or a chart spec. The tool returns a closed DTO (mark enum, fields, rows). Python maps that DTO to a spec. The server validates the spec. The browser only renders it.

| Option | Fit | Complexity | Lock-in | Streaming | Testing | License, last release | Cost |
|---|---|---|---|---|---|---|---|
| Plotly | `plotly.py` figure JSON → `react-plotly.js` | Figure JSON is large and loose | Plotly figure dialect | Client render of JSON | Snapshot the JSON | Both MIT. plotly.py 7.1.0 (2026-09-15). plotly.js 4.2.0 (2026-10-29). react-plotly.js 4.1.0 (2026-07-29), wrapper only | $0. No Chart Studio required |
| Vega-Lite | Altair → spec → `react-vega` / `vega-embed` | Small JSON, published JSON Schema | Vega-Lite schema version | Same | `jsonschema` in pytest, no browser | BSD-3-Clause: Altair 6.3.0 (2026-09-15, [LICENSE](https://github.com/vega/altair/blob/v6.3.0/LICENSE)), vega-lite 6.5.0 (2026-10-08), vega 6.4.0 (2026-08-14), vega-embed 7.3.0 (2026-09-23). react-vega 8.0.0 (2025-08-27); BSD-3-Clause in [package.json](https://github.com/vega/react-vega/blob/master/package.json); npm `license` field empty | $0 |
| ECharts | Strong canvas renderer, option JSON | No Python schema path checked | Option object | Same | Snapshot only | echarts 6.1.0 (2026-05-19) Apache-2.0. echarts-for-react 3.0.6 (2026-01-21) MIT | $0 |
| Recharts | Hand-written React components | You grow a private chart API | React components | Same | Component tests | MIT, 3.10.1 (2026-07-25) | $0 |

**Recommendation: Vega-Lite.** Altair 6 writes Vega-Lite 6 (`altair.vegalite.v6`). Its generator uses `https://vega.github.io/schema/vega-lite/{version}.json`. The main-branch pin seen was vega-lite v6.4.1; that the 6.3.0 tag matches is UNVERIFIED. Validate with `jsonschema`, inline rows as `data.values`, and reject `data.url` and `transform.calculate` (Vega expressions are a language). `react-vega` peers `vega-embed@^7` and has had no npm release since 2025-08-27, so pin `vega-embed` yourself.

Official plotly.js 4.2.0 sizes ([dist/README](https://github.com/plotly/plotly.js/blob/v4.2.0/dist/README.md)): full min+gzip **1.49 MB**; `basic` (bar, pie, scatter) **402 KB** gzip; `cartesian` (adds histogram, heatmap, box) **506 KB** gzip. bundlephobia, separate packages, not a combined build: vega 182 KB gzip, vega-lite 90 KB gzip, vega-embed wrapper 21 KB gzip. echarts full 368 KB gzip. recharts 150 KB gzip. A combined Vega webpack size was not built. Hebrew labels are Unicode; set `dir=ltr` on the chart node. Vega’s RTL axis behavior is UNVERIFIED.

## 4. Evaluation and observability

| Option | Fit | Complexity | Lock-in | Streaming | Testing | License, last release | Cost |
|---|---|---|---|---|---|---|---|
| Your harness + JSON traces | Already scores trajectories and the grounding rule | Done | None | n/a | The 70 questions | Yours | $0 |
| Langfuse | Trace UI, scores, prompts | Web + worker + Postgres + ClickHouse + Redis/Valkey + blob ([architecture](https://langfuse.com/self-hosting), read 2026-11-04). Production floor on the scaling page: web 2 CPU/4 GiB, worker 2/4, Postgres 2/4, Redis 1/1.5, ClickHouse 2/8 | Project schema; ClickHouse Inc. copyright | Ingest API | Duplicates the harness | MIT outside `ee/` ([LICENSE](https://github.com/langfuse/langfuse/blob/main/LICENSE)). Client SDK 5.1.0 (2026-10-30) MIT. EE key for SCIM, audit, retention | $0 license. The laptop demo pays in RAM |
| Phoenix | One lighter trace/eval UI | `phoenix serve` or one container. No ClickHouse/Redis in the deploy overview | ELv2 | OTel / OpenInference | Second scorer | **Elastic-2.0**, PyPI `arize-phoenix` 21.0.0 (2026-10-30). [LICENSE](https://github.com/Arize-ai/phoenix/blob/main/LICENSE) forbids offering a substantial feature set as a hosted service, and has a patent-termination clause. Docs call it open source; ELv2 is not OSI | $0 to self-host. No feature gate stated |
| OTel GenAI semconv | Attribute names only | A spec, status **Development** ([spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)) | Names still move (`gen_ai.system` already became `gen_ai.provider.name`) | n/a | n/a | Apache-2.0 spec. Dedicated repo has no stable cut; tag status UNVERIFIED beyond the Development banner | $0 |
| promptfoo | Prompt in, assert out | Node CLI | Its assertion files | n/a | Weak fit for tool trajectories | MIT, npm 0.125.1 (2026-10-25). PyPI `promptfoo` 0.2.0 is a different package; ignore it | $0 |
| DeepEval | LLM-as-judge metrics | Pytest plugin, Confident AI cloud | Judge scores instead of `{F#}` checks | Optional OTel to Confident | Conflicts with the deterministic validator | Apache-2.0, 4.3.3 (2026-11-04). Telemetry on unless `DEEPEVAL_TELEMETRY_OPT_OUT=1` ([docs](https://deepeval.com/docs/faq)) | $0 library. Cloud is paid |
| Inspect AI | A full task/solver/scorer harness | Custom solver to host your loop | Inspect logs | n/a | You would re-home the 70 questions | MIT, `inspect-ai` 0.3.287 (2026-10-31), [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | $0 |

**Recommendation: none.** The harness already checks the thing that matters, which is that every number came from a finding. Langfuse’s MIT core is real and the install is four datastores. Phoenix is smaller and the ELv2 service ban matters if this workspace is later hosted for other people. DeepEval and promptfoo grade the wrong object. Inspect is another harness. Pydantic Evals, mentioned in the Pydantic AI README, comes with the same adoption decision as Agent.

Keep writing JSON traces with model id, tool-call sequence, and validator pass/fail. Using today’s `gen_ai.provider.name`, `gen_ai.request.model`, and `gen_ai.usage.*` strings in that JSON is cheap and does not require a collector. Do not build dashboards on those names while the spec stays Development.
