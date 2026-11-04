"""Grounded answers: the model writes prose with finding placeholders; code validates and renders.

Answer object (from the model):
  {"headline": str, "body": str, "claims": [{"kind": "fact|inference|hypothesis", "text": str, "support": ["F3", ...]}],
   "assumptions": [str], "limitations": [str]}
Placeholders: {F12} -> formatted value with unit; {F12.label}; {F12.period}; {F12.class}; {F12.source}.

Guarantees enforced here (not by prompt):
  1. every placeholder resolves to a finding returned in this session;
  2. free text contains NO numerals except allowlisted tokens (years, FY/CY labels, airport codes, finding ids,
     ordinal list markers) — every number the reader sees comes from a finding;
  3. fact/inference claims cite ≥1 finding; hypotheses are labelled as such;
  4. forecast/estimated/hypothesis/exploratory values are visibly labelled at the point of use;
  5. evidence table, methodology and caveats are appended automatically from the cited findings.
"""
from __future__ import annotations

import re
from typing import Any

from .evidence import EvidenceStore, Finding, InvalidSpec

PH = re.compile(r"\{(F\d+)(?:\.(label|period|class|source|value|definition))?\}")
# numerals allowed in prose: 4-digit years 1990-2060, FY/CY+year, 'T-100', 'T12', list markers like '1.' at line start
ALLOW = re.compile(r"\b(?:19[9]\d|20[0-6]\d)\b|\b(?:FY|CY)\s?\d{2,4}\b|\bT-100\b|\bT12\b|^\s*\d+[.)]\s|\bQ[1-4]\b|"
                   r"\b[A-Z][A-Z0-9]{1,3}\b", re.M)   # codes must START with a letter (LAX, F12, Q1); '26M' is a number
NUM = re.compile(r"\d")
LABELLED = {"forecast": "FAA forecast", "estimated": "estimate", "hypothesis": "hypothesis", "exploratory": "exploratory query"}


def fmt_value(f: Finding) -> str:
    v = f.value
    if v is None:
        return "n/a (not established)"
    if isinstance(v, str):
        return v
    if f.fmt == "pct":
        s = f"{v * 100:.1f}%"
    elif f.fmt == "usd":
        s = f"${v / 1e9:,.2f}B" if abs(v) >= 1e9 else f"${v / 1e6:,.1f}M" if abs(v) >= 1e6 else f"${v:,.0f}"
    elif f.fmt == "minutes":
        s = f"{v:.1f} min"
    elif f.fmt == "ratio":
        s = f"{v:.3f}"
    else:
        if abs(v) >= 1e6:
            s = f"{v / 1e6:,.2f}M"
        elif abs(v) >= 100 or float(v).is_integer():
            s = f"{v:,.0f}"
        else:
            s = f"{v:,.2f}"
        unit = f.unit if f.unit and not f.unit.startswith("points") else ""
        if unit and unit not in ("ratio",):
            s = f"{s} {unit}"
    tag = LABELLED.get(f.epistemic_class)
    return f"{s} ({tag})" if tag else s


def _strip_allowed(text: str) -> str:
    t = PH.sub("", text)
    return ALLOW.sub("", t)


def validate(answer: dict[str, Any], store: EvidenceStore) -> list[str]:
    errs = []
    if not isinstance(answer, dict) or not answer.get("headline") or "body" not in answer:
        return ["answer must have 'headline' and 'body'"]
    texts = {"headline": answer["headline"], "body": answer["body"],
             **{f"claims[{i}]": c.get("text", "") for i, c in enumerate(answer.get("claims", []))},
             **{f"assumptions[{i}]": a for i, a in enumerate(answer.get("assumptions", []))},
             **{f"limitations[{i}]": a for i, a in enumerate(answer.get("limitations", []))}}
    for where, t in texts.items():
        for fid, _ in PH.findall(t or ""):
            if fid not in store:
                errs.append(f"{where}: placeholder {{{fid}}} does not refer to a finding from this session")
        rest = _strip_allowed(t or "")
        bad = re.findall(r"[^\s]*\d[^\s]*", rest)
        if bad:
            errs.append(f"{where}: numbers must come from findings via placeholders; found literal(s) {bad[:5]}")
    for i, c in enumerate(answer.get("claims", [])):
        kind = c.get("kind")
        if kind not in ("fact", "inference", "hypothesis"):
            errs.append(f"claims[{i}]: kind must be fact|inference|hypothesis")
        sup = c.get("support") or []
        if kind in ("fact", "inference") and not sup:
            errs.append(f"claims[{i}]: a {kind} must cite at least one finding in 'support'")
        for fid in sup:
            if fid not in store:
                errs.append(f"claims[{i}]: support {fid} is not a finding from this session")
    return errs


def render(answer: dict[str, Any], store: EvidenceStore) -> dict[str, Any]:
    errs = validate(answer, store)
    if errs:
        raise InvalidSpec("answer failed grounding validation", errors=errs)
    used: list[str] = []

    def sub(m):
        fid, attr = m.group(1), m.group(2)
        f = store.get(fid)
        used.append(fid)
        if attr in (None, "value"):
            return fmt_value(f)
        if attr == "label":
            return f.label
        if attr == "period":
            return f.window.get("label", "")
        if attr == "class":
            return f.epistemic_class
        if attr == "definition":
            return f.definition
        return "; ".join(s.label() for s in f.sources)

    def r(t):
        return PH.sub(sub, t or "")
    lines = [f"## {r(answer['headline'])}", "", r(answer["body"])]
    claims = answer.get("claims", [])
    if claims:
        lines += ["", "**Findings and reasoning**"]
        for c in claims:
            tag = {"fact": "Fact", "inference": "Inference", "hypothesis": "Hypothesis (not established by the data)"}[c["kind"]]
            sup = ", ".join(c.get("support") or [])
            lines.append(f"- *{tag}*: {r(c['text'])}" + (f" [{sup}]" if sup else ""))
            used += c.get("support") or []
    if answer.get("assumptions"):
        lines += ["", "**Assumptions**"] + [f"- {r(a)}" for a in answer["assumptions"]]
    # evidence appendix (automatic)
    ids = list(dict.fromkeys(used))
    fs = [store.get(i) for i in ids]
    expanded = list(fs)
    for f in fs:                      # include direct inputs of derived findings, one level
        expanded += [store.get(i) for i in f.inputs[:6] if i in store and store.get(i) not in expanded]
    if expanded:
        lines += ["", "**Evidence**", "", "| id | finding | value | class | period | sources | coverage |", "|---|---|---|---|---|---|---|"]
        for f in expanded:
            cov = f"{f.coverage['ratio']:.0%} ({f.coverage['window']})" if f.coverage and f.coverage.get("ratio") is not None else ""
            lines.append(f"| {f.id} | {f.label} | {fmt_value(f)} | {f.epistemic_class} | {f.window.get('label', '')} | "
                         f"{'; '.join(s.label() for s in f.sources)} | {cov} |")
        defs = {}
        for f in expanded:
            defs.setdefault(f.metric_id, f.definition)
        lines += ["", "**Methodology**"] + [f"- `{k}`: {v}" for k, v in defs.items()]
        cav = list(dict.fromkeys(c for f in expanded for c in f.caveats))
        lim = answer.get("limitations", [])
        if cav or lim:
            lines += ["", "**Caveats and limitations**"] + [f"- {c}" for c in cav] + [f"- {r(x)}" for x in lim]
    return {"markdown": "\n".join(lines), "cited_findings": ids}
