"""ONE live Groq end-to-end question with a hard ceiling of 5 generation requests. Run only deliberately.

    .venv/bin/python tools/groq_smoke.py          # needs ./scripts/configure-groq-key.sh first

Guarantees (checked before any call; the script exits without calling the API if one fails):
  * the model is one of the supported Groq tool-calling models and is listed for this account
    (GET /openai/v1/models: a catalog lookup, not a generation request);
  * at most 5 generation requests IN TOTAL for this authorisation: a persistent counter
    (data/app/groq_smoke_counter.json, independent of the daily budget, survives restarts) is incremented BEFORE each
    request, and the agent's step limit is set to what remains;
  * requests are also counted in the app's Groq daily log (data/app/groq_usage.jsonl);
  * no retries, no second question, no other provider is used. The API key is never printed.
Writes eval/runs/groq_smoke/report.json (git-ignored).
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


def model_in_catalog(model: str, key: str) -> tuple[bool, str]:
    import ssl
    import urllib.error
    import urllib.request
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    req = urllib.request.Request("https://api.groq.com/openai/v1/models",
                                 headers={"Authorization": f"Bearer {key}", "User-Agent": "airport-intel"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            ids = {m.get("id") for m in json.loads(r.read()).get("data", [])}
        return (model in ids), ("listed" if model in ids else "not listed for this account")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, type(e).__name__


def main() -> int:
    from airport_data.config import get_paths, load_env, load_groq_key
    load_env()
    os.environ.setdefault("AIRPORT_ALLOW_GROQ", "1")          # running this script is the explicit opt-in
    from airport_agent.models import GROQ_MODELS, GroqBackend, ModelError
    key = load_groq_key()
    model = os.environ.get("AIRPORT_GROQ_MODEL", "openai/gpt-oss-120b")
    problems = ([] if key else ["no Groq key (run ./scripts/configure-groq-key.sh)"]) + \
        ([] if model in GROQ_MODELS else [f"model {model!r} is not a supported Groq tool-calling model"])
    if problems:
        print("NOT RUN (no API call made):\n  - " + "\n  - ".join(problems))
        return 2
    try:
        g = GroqBackend(model=model)
    except ModelError as e:
        print(f"NOT RUN (no API call made): {e}")
        return 2
    counter = Path(os.environ.get("AIRPORT_GROQ_SMOKE_COUNTER") or get_paths().app / "groq_smoke_counter.json")
    used = json.loads(counter.read_text())["used"] if counter.exists() else 0
    remaining = CEILING - used
    if remaining <= 0:
        print(f"NOT RUN: the smoke-test allowance of {CEILING} requests is used up ({used}).")
        return 2
    if g.requests + remaining > g.max_requests:
        print(f"NOT RUN: {g.requests}/{g.max_requests} Groq requests already used today; this test could need {remaining}.")
        return 2
    ok, info = model_in_catalog(g.model, key)
    del key
    if not ok:
        print(f"NOT RUN: model {g.model!r} not confirmed in the Groq catalog ({info}).")
        return 2
    print(f"model={g.model} (catalog: {info})  Groq requests today before: {g.requests}/{g.max_requests}  "
          f"smoke allowance left: {remaining}  per-request context cap: {g.max_context_tokens}")

    class Capped:                       # persistent guard, independent of the daily budget and of restarts
        name, model, max_context_tokens = "groq", g.model, g.max_context_tokens

        def __init__(self):
            self.n = 0

        def complete(self, system, messages, tools):
            u = json.loads(counter.read_text())["used"] if counter.exists() else 0
            if u >= CEILING:
                raise ModelError(f"smoke-test ceiling of {CEILING} requests reached")
            counter.parent.mkdir(parents=True, exist_ok=True)
            counter.write_text(json.dumps({"used": u + 1, "ceiling": CEILING}))     # count BEFORE the call
            self.n += 1
            return g.complete(system, messages, tools)

    from airport_agent.runtime import Agent, Limits
    cb = Capped()
    agent = Agent(cb, limits=Limits(max_steps=remaining, max_tool_calls=20, wall_clock_s=420))
    r = agent.ask(QUESTION)
    report = {"question": QUESTION, "model": g.model, "kind": r.kind, "generation_requests": cb.n,
              "groq_daily": {"after": g.requests, "max": g.max_requests}, "ratelimit_last": g.rate,
              "tool_calls": [{"tool": c["tool"], "error": c["error"], "input": c["input"]} for c in r.tool_calls],
              "tokens": {"input": r.usage.input_tokens, "output": r.usage.output_tokens},
              "errors": [e[:300] for e in r.errors], "cited_findings": r.cited_findings,
              "claim_labels": [c.get("label") for c in (r.structured or {}).get("claims", [])],
              "markdown": r.markdown}
    out = ROOT / "eval" / "runs" / "groq_smoke"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "markdown"}, indent=2, default=str))
    print("\n--- rendered answer ---\n" + r.markdown)
    return 0 if r.kind == "answer" else 1


if __name__ == "__main__":
    raise SystemExit(main())
