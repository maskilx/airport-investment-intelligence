"""ONE live Gemini end-to-end question with a hard ceiling of 5 model requests. Run only deliberately.

    .venv/bin/python tools/gemini_smoke.py            # reads .env (AIRPORT_MODEL=gemini, AIRPORT_ALLOW_GEMINI=1, key)

Guarantees (checked before any call; the script exits without calling the API if one fails):
  * configured model is a free-tier Flash id and AIRPORT_ALLOW_PAID is not set (no paid model, no fallback);
  * requests are counted in the app's persistent daily log (data/app/gemini_usage.jsonl), the same budget the UI uses;
  * today's used + 5 leaves most of the daily budget for manual use;
  * at most 5 generateContent requests: the agent's step limit AND a counting wrapper both stop at 5;
  * no retries, no second question, web research off. The API key is never printed.
Writes eval/runs/gemini_smoke/report.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CEILING = 5
QUESTION = ("Compare congestion levels at LAX and SNA over the latest common reporting period. "
            "Explain the metrics, scope, supporting evidence and uncertainty.")


def main() -> int:
    from airport_data.config import load_env
    load_env()
    from airport_agent.models import FREE_TIER_MODEL, GeminiBackend, ModelError
    problems = []
    if os.environ.get("AIRPORT_MODEL", "offline").lower() != "gemini":
        problems.append("AIRPORT_MODEL is not 'gemini'")
    if os.environ.get("AIRPORT_ALLOW_GEMINI") != "1":
        problems.append("AIRPORT_ALLOW_GEMINI is not 1")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        problems.append("no GEMINI_API_KEY (set it in .env; it is git-ignored)")
    if os.environ.get("AIRPORT_ALLOW_PAID"):
        problems.append("AIRPORT_ALLOW_PAID is set: refusing (paid models must stay disabled)")
    model = os.environ.get("AIRPORT_GEMINI_MODEL", "gemini-3.8-flash")
    if not FREE_TIER_MODEL.match(model):
        problems.append(f"model {model!r} is not a free-tier Flash id")
    if problems:
        print("NOT RUN (no API call made):\n  - " + "\n  - ".join(problems))
        return 2
    try:
        g = GeminiBackend()
    except ModelError as e:
        print(f"NOT RUN (no API call made): {e}")
        return 2
    used0, cap = g.requests, g.max_requests
    if used0 + CEILING > cap:
        print(f"NOT RUN: {used0}/{cap} requests already used today; this test could need {CEILING}.")
        return 2
    print(f"model={g.model}  daily budget before: {used0}/{cap}  ceiling for this test: {CEILING}")

    class Capped:                        # second, independent guard on top of the agent's step limit
        name, model = "gemini", g.model

        def __init__(self):
            self.n = 0

        def complete(self, system, messages, tools):
            if self.n >= CEILING:
                raise ModelError(f"smoke-test ceiling of {CEILING} requests reached")
            self.n += 1
            return g.complete(system, messages, tools)

    from airport_agent.runtime import Agent, Limits
    cb = Capped()
    agent = Agent(cb, limits=Limits(max_steps=CEILING, max_tool_calls=20, wall_clock_s=240))
    events = []
    r = agent.ask(QUESTION, on_event=lambda e: events.append(e))
    report = {
        "question": QUESTION, "model": g.model, "kind": r.kind, "model_requests": cb.n,
        "daily_budget": {"before": used0, "after": g.requests, "max": cap, "remaining": cap - g.requests},
        "tool_calls": [{"tool": c["tool"], "error": c["error"], "input": c["input"]} for c in r.tool_calls],
        "tokens": {"input": r.usage.input_tokens, "output": r.usage.output_tokens},
        "errors": [e[:300] for e in r.errors], "cited_findings": r.cited_findings,
        "claim_labels": [c.get("label") for c in (r.structured or {}).get("claims", [])],
        "scoring_or_method_sections": bool((r.structured or {}).get("methodology")),
        "markdown": r.markdown,
    }
    out = ROOT / "eval" / "runs" / "gemini_smoke"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "markdown"}, indent=2, default=str))
    print("\n--- rendered answer ---\n" + r.markdown)
    return 0 if r.kind == "answer" else 1


if __name__ == "__main__":
    raise SystemExit(main())
