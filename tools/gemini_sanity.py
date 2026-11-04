"""Small, final Gemini API sanity check (run only deliberately; it makes real free-tier API calls).

    AIRPORT_ALLOW_GEMINI=1 GEMINI_API_KEY=... .venv/bin/python tools/gemini_sanity.py [--model gemini-...] [--max-requests 24]

Checks, in at most --max-requests generateContent calls (default 24, hard stop, no fallback, no retries):
  1. connection: the model is listed by the API (models.get — not a generation call) and answers one request;
  2. tool use: the model calls our tools;
  3. multi-step: a two-airport comparison reaches a validated compose_answer;
  4. grounding: the answer passed the validator, cites findings, and every number in the rendered prose sits in a
     substituted placeholder (checked again here against the structured output);
  5. follow-up: a question that only says "that airport" is answered about an airport from the previous turn.
Writes eval/runs/gemini_sanity/report.json (model, requests, tokens, latency, errors per turn). Web research is off.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

QUESTIONS = [
    ("multi_step", "Compare LA and Santa Ana airport congestion levels."),
    ("follow_up", "How has passenger traffic at that second airport changed over the last year?"),
]


def model_exists(model: str, key: str) -> tuple[bool, str]:
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
                                 headers={"x-goog-api-key": key})
    try:
        import ssl

        import certifi
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context(cafile=certifi.where())) as r:
            d = json.loads(r.read())
            return True, d.get("displayName", model)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"


def numbers_outside_chips(structured: dict, evidence=None) -> list[str]:
    """Values are wrapped as ⟦F#|value⟧ and labels/names/periods/definitions are substituted from cited findings;
    after removing all of those, any remaining digit (beyond years/codes) is a leak."""
    from airport_analytics.render import ALLOW
    subs = []
    for fid in structured.get("evidence", []):
        if evidence is not None and fid in evidence:
            f = evidence.get(fid)
            subs += [f.label, f.label.split(" — ")[0], f.window.get("label", ""), f.definition]
    subs = sorted({x for x in subs if x}, key=len, reverse=True)
    bad = []
    for t in [structured.get("headline", ""), structured.get("body", "")] + [c["text"] for c in structured.get("claims", [])]:
        rest = re.sub(r"⟦[FW]\d+\|[^⟧]*⟧", "", t)
        for x in subs:
            rest = rest.replace(x, "")
        rest = re.sub(r"\[[^\]]*\]\([^)]*\)", "", rest)               # links to sources
        rest = re.sub(r"\d{4}-\d{2}(?:…\d{4}-\d{2})?", "", rest)      # substituted periods
        bad += re.findall(r"\S*\d\S*", ALLOW.sub("", rest))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("AIRPORT_GEMINI_MODEL", "gemini-3.8-flash"))
    ap.add_argument("--max-requests", type=int, default=24)
    a = ap.parse_args()
    if os.environ.get("AIRPORT_ALLOW_GEMINI") != "1" or not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print("Refusing: set AIRPORT_ALLOW_GEMINI=1 and GEMINI_API_KEY to run this real-API check.")
        return 2
    key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
    out_dir = ROOT / "eval/runs/gemini_sanity"
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"model_requested": a.model, "max_requests": a.max_requests, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "turns": [], "checks": {}}
    ok, info = model_exists(a.model, key)
    report["checks"]["model_listed"] = {"ok": ok, "detail": info}
    if not ok:
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 1

    from airport_agent.memory import ConversationStore
    from airport_agent.models import GeminiBackend
    from airport_agent.runtime import Agent, Limits
    backend = GeminiBackend(model=a.model, max_requests=a.max_requests, usage_log=out_dir / "usage.jsonl")
    agent = Agent(backend, store=ConversationStore(out_dir / "conversation.sqlite"), conv_id=f"sanity-{int(time.time())}",
                  limits=Limits(max_steps=10, max_tool_calls=20, wall_clock_s=300))
    prev_codes: set[str] = set()
    for kind, q in QUESTIONS:
        if backend.requests >= a.max_requests:
            report["turns"].append({"kind": kind, "skipped": "request budget exhausted"})
            break
        r0 = backend.requests
        r = agent.ask(q)
        codes = {f.subject.get("airport_code") for f in (agent.evidence.get(i) for i in r.cited_findings)} - {None}
        t = {"kind": kind, "question": q, "result": r.kind, "requests": backend.requests - r0, "latency_s": r.trace["latency_s"],
             "usage": r.trace["usage"], "tools": [c["tool"] + ("!" + c["error"] if c["error"] else "") for c in r.tool_calls],
             "cited": r.cited_findings, "airports_cited": sorted(codes), "errors": r.errors,
             "headline": (r.structured or {}).get("headline") or r.markdown[:300],
             "leaks": numbers_outside_chips(r.structured, agent.evidence) if r.structured else []}
        report["turns"].append(t)
        if kind == "multi_step":
            prev_codes = codes
        print(json.dumps(t, indent=1))
    t1 = report["turns"][0] if report["turns"] else {}
    t2 = report["turns"][1] if len(report["turns"]) > 1 else {}
    report["checks"].update({
        "connection": {"ok": any(x.get("requests") for x in report["turns"])},
        "tool_use": {"ok": bool(t1.get("tools"))},
        "multi_step_valid_answer": {"ok": t1.get("result") == "answer" and len(t1.get("airports_cited", [])) >= 2},
        "grounding": {"ok": t1.get("result") == "answer" and not t1.get("leaks") and bool(t1.get("cited"))},
        "follow_up_uses_context": {"ok": t2.get("result") == "answer" and bool(set(t2.get("airports_cited", [])) & prev_codes),
                                   "note": "expects the follow-up to be about an airport from turn 1 (SNA)"},
    })
    report["totals"] = {"requests": backend.requests, **agent.usage.__dict__}
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report["checks"], indent=2), json.dumps(report["totals"]))
    return 0 if all(c["ok"] for c in report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
