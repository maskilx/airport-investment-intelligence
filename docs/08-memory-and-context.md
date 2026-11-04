# Memory & Context Architecture (decision record)

**Status:** decided and implemented (`src/airport_agent/memory.py`).

**Research:** an independent Grok 4.7 research brief compared these systems from their primary docs:
- Letta/MemGPT, Mem0, Zep/Graphiti, LangMem + LangGraph store, LlamaIndex Memory;
- Anthropic and OpenAI context-management guidance, Google ADK sessions;
- the lost-in-the-middle paper (Liu et al., TACL 2024) and summary-faithfulness work (Maynez et al., ACL 2020).

## The invariant that drives the design

> A summary must never become an authoritative source of numerical facts.

Every surveyed memory framework stores **model-written paraphrases** as memory:
- Mem0 runs LLM fact extraction;
- Graphiti uses LLM-extracted edges;
- LangMem and LlamaIndex use fact blocks;
- Letta uses self-edited memory blocks;
- OpenAI compaction produces an opaque encrypted item.

A paraphrase of "SFO seat factor 84.2% (2025-08…2026-07, T-100)" will eventually drop the period, round the value, or move it onto another airport. Abstractive summaries contain unsupported content even in a single hop (Maynez et al.), and chained summaries compound that. So no framework is adopted as the memory layer. We borrow three patterns:
- the session / state / archive split from Google ADK;
- *supersede, never delete* from Graphiti;
- tool-result clearing from Anthropic, its lightest-touch compaction.

## Five layers, five owners

| Layer | What | Owner | May contain numbers? | Stored |
|---|---|---|---|---|
| Transcript | every user/assistant/tool message, append-only | runtime | yes (raw) | SQLite `messages` |
| Evidence | findings `F#`: value, unit, definition, window, sources + vintages, caveats, inputs, reproducing spec | analytics engine | **yes; the only authoritative source** | SQLite `findings` (immutable rows) |
| State | entities by recency, metrics, windows, assumptions (A#, active/superseded/retracted), decisions (→F#), answers (headline + cited F#), preferences | code (deterministic, from tool calls) + validated `update_memory` | no (F#/A# references only) | SQLite `state` + `state_log` |
| Rolling summary | narrative of turns that left the recent window | model, **validated**; extractive fallback | **no** (regex-rejected) | SQLite `summaries` |
| External evidence | web pages: URL, title, retrieved-at, excerpt | web tools | quoted only, labelled `external_web` | per-conversation `W#` (separate namespace) |

Finding ids never change and are never reused. A conversation reloaded from disk gets new ids continuing from `max(n)+1`. A correction never edits a finding. The model re-runs the analysis under the new assumption, which produces new F#s, and the old assumption is marked `superseded` with a pointer to its replacement. Both stay inspectable.

## Building context per request (no full-history resend)

`ContextBuilder.build()` assembles, under a token budget (default 24k for messages + memory; ≈4 chars/token, provider-neutral):

1. **Recent turns verbatim**, newest first until ~55% of the budget is used. Tool results from *previous* turns are replaced with pointers: `[earlier tool result; findings F12…F20 (9) are stored — use get_finding/recall]`.
2. **Memory block**, placed in the *current* user message, right next to the question. Liu et al. show recall is worst in the middle of a long context, so pinned facts go at the end. It contains:
   - conversation state: entities in focus, metrics, active assumptions, superseded assumptions marked "do not use", decisions, preferences;
   - a **findings index** with values rendered from the evidence store at request time, never from memory. Relevance = cited in an earlier answer, plus about a focus entity, plus lexical overlap with the question;
   - the rolling summary, only when some turns are outside the verbatim window;
   - **retrieved earlier turns**: BM25 over the older turns' question, headline and cited ids, with airport codes and F-ids as exact tokens.
3. **Recall tool** (`recall`): the model can search the whole transcript and findings on demand, so nothing is ever unreachable.

**Why lexical and not a vector DB:**
- One conversation means hundreds of turns, not millions.
- The things users refer back to are names, codes, metrics and finding ids, where exact matching beats embeddings.
- No embedding calls are spent, which keeps us inside the free-tier budget.
- No extra service is needed.

The upgrade path, if cross-conversation memory at scale is ever needed, is SQLite FTS5 and then embeddings behind the same `retrieve()` signature.

## Compaction

- **When:** `maybe_compact()` runs after a turn, once at least 6 turns fall outside the verbatim window and are not yet covered by the summary.
- **What it summarises:** only the user question, the answer headline and the cited ids. Raw tool payloads are never summarised; they stay in the findings.
- **Summariser:** in production, the model. It is accepted only if `summary_is_safe()` passes, meaning the text has no digits except F#/A# ids, years and FY/CY tokens.
- **Fallback:** otherwise a deterministic extractive summary is stored (one line per turn, digits in questions masked), with no extra model call.
- **Never summarised:** findings, assumptions, the entity table, corrections.

## References ("the airport we discussed earlier", "the second one", "same period")

1. Code first: `state.focus()` orders entities by last-mentioned turn. The memory block lists them in that order, with their kinds.
2. The model resolves the reference against that list and states the assumption ("Assuming 'that airport' = BOS, discussed in turn 3"). If two entities of the same kind are equally plausible, the system prompt requires a clarification question.
3. The resolved code still goes through `resolve_entities` / `run_analysis`, so a mis-resolution cannot invent an airport.

## Corrections and contradictory assumptions

`update_memory` is a validated tool with these actions:
- `set_assumption` (optional `replaces: A#`);
- `retract_assumption`;
- `note_decision` (text must be number-free, support = F# list);
- `set_preference`.

Superseded assumptions stay visible as "No longer valid (do not use)", so the model sees the history of the correction and does not regress to the old assumption.

## Tested without any model calls (`tests/test_memory.py`)

- Persistence round-trip: transcript, findings, state; F-ids continue after reload.
- A poisoned summariser that inserts a percentage is rejected, and the extractive summary is stored instead.
- A 120-turn conversation stays within the token budget. The required finding appears in the memory block even after its turn left the verbatim window, and old tool payloads are collapsed to pointers.
- Superseded assumptions are marked; decisions with numbers are rejected.
- BM25 retrieval finds the turn about a named airport and gives exact matches to codes and F-ids.
- Agent-level: a follow-up "and how does that compare with the airport we looked at first?" resolves through state (scripted backend).
