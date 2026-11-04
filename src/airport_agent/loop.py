"""Provider-agnostic agent loop over the analytics tools.

The model decides WHAT to compute; the engine computes; the renderer guarantees grounding.
Final outputs are either:
  * a rendered answer produced by the `compose_answer` tool (grounding validated), or
  * a plain-text CLARIFICATION / REFUSAL that contains no numerals (nothing to ground).
Anything else is sent back to the model with the reason (bounded), then falls back to an
evidence-only response — the loop never shows an unvalidated number.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from airport_analytics.render import ALLOW, PH
from airport_analytics.tools import Session, tool_schemas

SYSTEM_PROMPT = """You are an airport-investment analyst assistant for a firm that invests in US airport modernization.
You answer ONLY with evidence produced by the tools. Workflow:
1. Identify entities (airports, regions), metrics, periods, comparisons. Call resolve_entities for places.
   - Ambiguous place (e.g. "Portland") and not a contrast that makes the intent clear -> ask a clarification question.
   - Contrast questions ("LA vs Santa Ana") -> bind each side to its most specific airport and STATE the assumption.
2. Use describe_catalog to pick valid metric ids; never invent ids. Compose analyses with run_analysis
   (ops: aggregate, rank, correlate, trend, anomaly, distribution, forecast_vs_actual, screen; metric transforms
   pct_change/abs_change/cagr). Multi-part questions = several run_analysis calls. Use derive for any arithmetic
   between findings. Use query_sql only when no catalog metric fits; its results are 'exploratory'.
3. Tool errors are information: out_of_coverage / not_applicable / insufficient_data / ambiguous_entity mean you
   must say what cannot be established (and why), or ask, or narrow the question. Never fill gaps yourself.
4. Finish with compose_answer: every number as a {F#} placeholder; claims labelled fact / inference / hypothesis
   with supporting finding ids; assumptions and limitations explicit. Distinguish observed, calculated, forecast,
   estimated values (the renderer labels them). Do not present hypotheses (causes, unmet demand, profitability) as
   facts. Unmet demand, terminal capacity, fares and profitability are NOT directly measured by this data — say so.
5. For investment rankings use op=screen (a screening rank, not a valuation) and mention its flags and ties.
If a question cannot be answered with the available data, reply with a short plain-text explanation (no numbers)
of what is missing, or answer the closest answerable part via compose_answer and state the gap."""


class ModelBackend(Protocol):
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> dict: ...


class AnthropicBackend:
    """Anthropic Messages API backend (optional dependency; needs ANTHROPIC_API_KEY)."""

    def __init__(self, model: str | None = None, max_tokens: int = 4096):
        import anthropic  # noqa: deferred so the engine has no hard dependency
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("AIRPORT_AGENT_MODEL", "claude-opus-5-5")
        self.max_tokens = max_tokens

    def complete(self, system, messages, tools):
        r = self.client.messages.create(model=self.model, system=system, messages=messages, tools=tools,
                                        max_tokens=self.max_tokens)
        return {"content": [b.model_dump() for b in r.content], "stop_reason": r.stop_reason}


class ScriptedBackend:
    """Deterministic backend for tests: replays a list of assistant turns (content blocks)."""

    def __init__(self, turns: list[list[dict]]):
        self.turns = list(turns)

    def complete(self, system, messages, tools):
        content = self.turns.pop(0) if self.turns else [{"type": "text", "text": "I cannot answer that."}]
        return {"content": content, "stop_reason": "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"}


@dataclass
class TurnResult:
    kind: str                         # answer | clarification | fallback
    markdown: str
    tool_calls: list[dict] = field(default_factory=list)
    cited_findings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _has_numbers(text: str) -> bool:
    return bool(re.search(r"\d", ALLOW.sub("", PH.sub("", text))))


class Agent:
    def __init__(self, backend: ModelBackend, session: Session | None = None, max_steps: int = 14):
        self.backend = backend
        self.session = session or Session()
        self.max_steps = max_steps
        self.history: list[dict] = []          # conversation across turns (follow-ups reuse findings)

    def ask(self, question: str) -> TurnResult:
        msgs = self.history + [{"role": "user", "content": question}]
        calls: list[dict] = []
        nudges = 0
        for _ in range(self.max_steps):
            out = self.backend.complete(SYSTEM_PROMPT, msgs, tool_schemas())
            blocks = out["content"]
            msgs.append({"role": "assistant", "content": blocks})
            uses = [b for b in blocks if b.get("type") == "tool_use"]
            if not uses:
                text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
                if text and not _has_numbers(text):
                    self.history = msgs
                    return TurnResult("clarification", text, calls)
                if nudges < 2:
                    nudges += 1
                    msgs.append({"role": "user", "content": "System: final answers containing numbers must be submitted "
                                                            "through compose_answer with {F#} placeholders."})
                    continue
                break
            results = []
            for u in uses:
                res = self.session.call(u["name"], u.get("input") or {})
                calls.append({"tool": u["name"], "input": u.get("input"), "error": res.get("error") if isinstance(res, dict) else None})
                if u["name"] == "compose_answer" and isinstance(res, dict) and "markdown" in res:
                    self.history = msgs + [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"],
                                                                          "content": "rendered"}]}]
                    return TurnResult("answer", res["markdown"], calls, res["cited_findings"])
                results.append({"type": "tool_result", "tool_use_id": u["id"],
                                "content": json.dumps(res, default=str)[:60_000]})
            msgs.append({"role": "user", "content": results})
        # fallback: evidence only, never unvalidated prose with numbers
        made = [c for c in calls if c["tool"] == "run_analysis" and not c["error"]]
        self.history = msgs
        return TurnResult("fallback", "I could not produce a validated answer. The analyses I ran are recorded "
                          f"({len(made)} successful analysis calls); please rephrase or narrow the question.", calls,
                          errors=["no validated compose_answer within step budget"])
