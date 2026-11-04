"""Agent evaluation: run questions through an external agent that may ONLY use our tool CLI, then score.

    python eval/run_eval.py run   --questions eval/questions.jsonl --out eval/runs/<name> [--ids q001,q002] [--parallel 6]
    python eval/run_eval.py score --questions eval/questions.jsonl --out eval/runs/<name>

The agent here is Grok (CLI, model grok-4.7, reasoning xhigh) restricted to one allowed command:
`.venv/bin/python -m airport_analytics call ...`. Scoring reads OUR artifacts (tool-call log, rendered answer),
not the agent's own prose, so a number can only count if it went through compose_answer.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

AGENT_BRIEF = """You are the reasoning layer of an airport-investment analytics assistant. You may ONLY obtain data by running
this command (one tool call per invocation; JSON args in single quotes):
  .venv/bin/python -m airport_analytics call <tool> '<json>' --session {session}
Tools: resolve_entities {{"terms":[...]}} | describe_catalog {{}} or {{"metric":"id"}} | run_analysis {{"spec":{{...}}}} |
derive {{"op":"difference|ratio|pct_difference|sum","findings":["F1","F2"]}} | query_sql {{"sql":"SELECT ..."}} |
get_finding {{"id":"F1"}} | compose_answer {{"answer":{{"headline":..,"body":..,"claims":[{{"kind":"fact|inference|hypothesis","text":..,"support":["F1"]}}],"assumptions":[..],"limitations":[..]}}}}
Start with describe_catalog to learn metric ids, ops and the analysis-spec format. Policies:
{policy}
FINISH: either a successful compose_answer (numbers ONLY as {{F#}} placeholders — literal numbers are rejected, fix and retry),
or, if you must ask the user or cannot answer, print one final line starting with CLARIFICATION: or CANNOT_ANSWER:
followed by plain text with no numbers. Question: {question}"""


def _policy() -> str:
    from airport_agent.loop import SYSTEM_PROMPT
    return SYSTEM_PROMPT


def run_one(q: dict, out: Path) -> dict:
    d = out / q["id"]
    d.mkdir(parents=True, exist_ok=True)
    sess = d / "session.pkl"
    for p in d.glob("session.pkl*"):
        p.unlink()
    prompt = AGENT_BRIEF.format(session=sess, policy=_policy(), question=q["question"])
    cmd = ["grok", "-m", "grok-4.7", "--reasoning-effort", "xhigh", "--disable-web-search", "--max-turns", "40",
           "--allow", "Bash(.venv/bin/python -m airport_analytics call:*)", "-p", prompt]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1500)
        (d / "agent_stdout.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
    except subprocess.TimeoutExpired:
        (d / "agent_stdout.txt").write_text("TIMEOUT")
    return {"id": q["id"], "done": True}


def score_one(q: dict, out: Path) -> dict:
    from airport_analytics.render import ALLOW, PH
    d = out / q["id"]
    log = [json.loads(l) for l in (d / "session.pkl.log.jsonl").read_text().splitlines()] if (d / "session.pkl.log.jsonl").exists() else []
    ans = (d / "session.pkl.answer.md").read_text() if (d / "session.pkl.answer.md").exists() else ""
    stdout = (d / "agent_stdout.txt").read_text() if (d / "agent_stdout.txt").exists() else ""
    tail = stdout.split("--- stderr ---")[0].strip().splitlines()
    final_line = next((l for l in reversed(tail) if l.startswith(("CLARIFICATION:", "CANNOT_ANSWER:"))), "")
    kind = "answer" if ans else ("clarification" if final_line.startswith("CLARIFICATION") else
                                 "cannot_answer" if final_line else "none")
    e = q.get("expect", {})
    text = (ans or final_line).lower()
    ops_used = {c["input"].get("spec", {}).get("op") for c in log if c["tool"] == "run_analysis" and isinstance(c.get("input"), dict)}
    blob = json.dumps(log).upper() + ans.upper()
    checks = {}
    checks["finished"] = kind != "none"
    checks["grounded"] = kind == "answer" or (kind in ("clarification", "cannot_answer") and
                                              not re.search(r"\d", ALLOW.sub("", PH.sub("", final_line))))
    if e.get("entities"):
        checks["entities"] = all(str(x).upper() in blob for x in e["entities"])
    if e.get("ops"):
        checks["ops"] = bool(set(e["ops"]) & ops_used)
    if e.get("must_clarify"):
        checks["clarify_or_assume"] = kind == "clarification" or "assum" in text
    if e.get("must_refuse_or_flag"):
        checks["refuse_or_flag"] = kind in ("cannot_answer", "clarification") or any(
            w in text for w in ("not established", "not available", "cannot", "not measured", "no data", "not in the data",
                                "does not include", "not directly", "unavailable", "limitation"))
    if e.get("must_state_assumption"):
        checks["assumption"] = "assum" in text or kind == "clarification"
    neg = re.compile(r"\b(not|no|cannot|can't|unavailable|without|lack|absent|isn't|aren't|does not|do not|neither|nor)\b")
    for ph in e.get("must_not_claim", []):
        hits = [m.start() for m in re.finditer(re.escape(ph.lower()), text)]
        # a mention inside a negation ("fares are not available") is a correct refusal, not a claim
        claimed = [h for h in hits if not neg.search(text[max(0, h - 80):h + len(ph) + 40])]
        checks[f"no_claim:{ph[:30]}"] = not claimed
    n_err = sum(1 for c in log if c.get("error"))
    return {"id": q["id"], "category": q["category"], "kind": kind, "n_calls": len(log), "n_tool_errors": n_err,
            "ops_used": sorted(o for o in ops_used if o), "checks": checks, "pass": all(checks.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "score"])
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids")
    ap.add_argument("--parallel", type=int, default=6)
    a = ap.parse_args()
    qs = [json.loads(l) for l in Path(a.questions).read_text().splitlines() if l.strip()]
    if a.ids:
        want = set(a.ids.split(","))
        qs = [q for q in qs if q["id"] in want]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "run":
        with ThreadPoolExecutor(a.parallel) as ex:
            for r in ex.map(lambda q: run_one(q, out), qs):
                print(r, flush=True)
        return
    rows = [score_one(q, out) for q in qs]
    (out / "scores.json").write_text(json.dumps(rows, indent=1))
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        agg[r["category"]][0] += r["pass"]
        agg[r["category"]][1] += 1
    for c, (p, n) in sorted(agg.items()):
        print(f"{c:14s} {p}/{n}")
    print("TOTAL", sum(r["pass"] for r in rows), "/", len(rows))
    for r in rows:
        if not r["pass"]:
            print(" FAIL", r["id"], r["category"], r["kind"], {k: v for k, v in r["checks"].items() if not v})


if __name__ == "__main__":
    main()
