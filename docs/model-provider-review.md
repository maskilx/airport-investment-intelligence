# Model provider review: Groq

Researched on 2026-11-04 from Groq's official documentation. Sources are at the end. **No Groq API call has been made
by this project yet**, so account-specific limits are checked by `configure-groq-key.sh` (a catalog lookup) and read
from Groq's rate-limit response headers once you enter your key.

## Candidates

| Model id | Status | Context / max output | Price in / out per 1M tokens | Tool use | Notes |
|---|---|---|---|---|---|
| **`openai/gpt-oss-120b`** | **Production** | 131k / 65k | $0.15 / $0.60 (cached input $0.075) | Yes, no parallel tool calls | Strict structured outputs; automatic prompt caching; named by Groq as the replacement for every retired chat model |
| `openai/gpt-oss-20b` | Production | 131k / 65k | $0.075 / $0.30 | Yes, no parallel tool calls | About 2× faster, weaker multi-step planning |
| `qwen/qwen3.8-27b` | **Preview** ("may be discontinued at short notice") | 131k / 16k | $0.80 / $4.00 | Yes, parallel | Its predecessor qwen3.6-27b was shut down 2026-09-14 |
| `llama-3.3-70b-versatile` | Enterprise only since 2026-08-16 | n/a | Contact sales | n/a | Not available on the free or Developer tiers |
| `qwen/qwen3-32b`, `llama-4-*`, `kimi-k2-*` | Shut down | n/a | n/a | n/a | n/a |

**Choice: `openai/gpt-oss-120b`.**
* It is the strongest **production** tool-calling model available outside Enterprise.
* It is about 5× cheaper than Qwen 3.8.
* Its no-parallel-tools limitation fits our loop, which executes tools one step at a time anyway.

Qwen 3.8 (preview) and gpt-oss-20b (cheaper, faster, weaker) are supported alternatives (`AIRPORT_GROQ_MODEL`).
The app refuses any other model id.

## Free tier: the important constraint

Free-plan limits per model for gpt-oss-120b, gpt-oss-20b and qwen3.8: **30 RPM, 1,000 RPD, 8,000 tokens per minute,
200,000 tokens per day.** No credit card is needed for the free plan; upgrading to Developer requires a payment method.

Our agent's system prompt plus tool schemas are about 4.4k tokens before any conversation. A question takes 3–6 model
requests, so on the free tier:

* **Request size:** each request must stay under 8k tokens. The Groq backend caps the per-request context at 8,000 estimated tokens (conservative 3 chars/token, about 6k real tokens), plus a 1,500-token completion. Larger contexts are compacted to finding ids; if a request still does not fit, the turn stops with an explicit message.
* **Pacing:** consecutive requests within one minute exceed 8k TPM, so the backend reads `x-ratelimit-remaining-tokens` / `x-ratelimit-reset-tokens` and **waits** for the window (up to 65 s). That is pacing, not retrying.
* **Expected experience (inference):** a multi-step question takes about **1–4 minutes** on the free tier. 200k tokens per day allows roughly **10–25 questions per day**.

**Recommendation for the interview demo:** if responsiveness matters, upgrade the Groq account to the **Developer
(pay-as-you-go)** plan: 1,000 RPM and 250k TPM. Cost at $0.15/$0.60 per 1M tokens is about **$0.002–$0.01 per question**
(inference: 15–40k input tokens and 1–3k output tokens per question). Then set `AIRPORT_GROQ_MAX_CONTEXT_TOKENS=60000`.
That is your billing decision. The app never enables paid features by itself, and it has **no fallback** to Gemini or
offline when Groq fails.

## How the adapter fits (`GroqBackend`, `src/airport_agent/models.py`)
* **Same loop:** the same `Agent` loop, tool registry, memory and validation as Gemini and offline. Only message and tool-schema translation is provider-specific.
* **Request settings:** OpenAI-compatible `chat/completions` with `tools`, `tool_choice=auto`, `parallel_tool_calls=false`, temperature 0.2, `reasoning_effort=medium` and `include_reasoning=false` for gpt-oss.
* **Schemas:** `oneOf` and free-form objects are sent as JSON strings and decoded server-side (`decode_args`), since Groq documents `anyOf` only. Invalid tool-call JSON comes back to the model as a tool error.
* **Streaming:** the UI streams progress events (model steps, tool runs). The final answer is not token-streamed because it is validated first.
* **Separate from Gemini:**
  * Keychain service `airport-investment-intelligence-groq`;
  * daily budget `AIRPORT_GROQ_MAX_REQUESTS` (default 60), logged in `data/app/groq_usage.jsonl`;
  * smoke-test allowance `data/app/groq_smoke_counter.json` (5 requests in total).
* **Errors:** a 429 or 413 stops the turn with an explanation. No fallback.

## Sources
https://console.groq.com/docs/models · https://console.groq.com/docs/rate-limits · https://console.groq.com/docs/tool-use ·
https://console.groq.com/docs/structured-outputs · https://console.groq.com/docs/reasoning ·
https://console.groq.com/docs/prompt-caching · https://console.groq.com/docs/deprecations ·
https://console.groq.com/docs/billing-faqs · https://console.groq.com/docs/model/openai/gpt-oss-120b ·
https://console.groq.com/docs/model/qwen/qwen3.8-27b · free-tier 413 reports (third-party; the automated link check was redirected to groq.com, so not verified):
https://community.groq.com/t/gpt-oss-20b-free-tier-getting-413-errors/1411
