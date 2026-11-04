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

PH = re.compile(r"\{(F\d+)(?:\.(label|name|period|class|source|value|definition))?\}")
WPH = re.compile(r"\{(W\d+)\}")                       # external web evidence: renders as a link, carries no value
# numerals allowed in prose: 4-digit years 1990-2060, FY/CY+year, 'T-100', 'T12', list markers like '1.' at line start
ALLOW = re.compile(r"\b(?:19[9]\d|20[0-6]\d)\b|\b(?:FY|CY)\s?\d{2,4}\b|\bT-100\b|\bT12\b|^\s*\d+[.)]\s|\bQ[1-4]\b|"
                   r"\b[A-Z][A-Z0-9]{1,3}\b", re.M)   # codes must START with a letter (LAX, F12, Q1); '26M' is a number
NUM = re.compile(r"\d")
NUMBER_WORDS = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                          r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
                          r"ninety|hundred|thousand|million|billion|trillion|dozen|half|third|quarter|percent|"
                          r"double|twice|triple|tripled|doubled|halved)\b", re.I)
ALLOWED_WORD_USES = re.compile(r"\b(one of|at least one|no one|one or more|half-hour|quarter of an hour|which one|"
                               r"that one|this one|the one|each one|any one|one airport|one region)\b", re.I)


def _numeric_chars(t: str) -> list[str]:
    import unicodedata
    out = []
    for ch in t:
        if not ch.isascii():
            try:
                unicodedata.numeric(ch)
                out.append(ch)
            except (TypeError, ValueError):
                pass
    return out


def _codes_in(text: str, known: set[str]) -> set[str]:
    return {t for t in re.findall(r"\b[A-Z][A-Z0-9]{2,3}\b", text) if t in known}
LABELLED = {"forecast": "FAA forecast", "estimated": "estimate", "hypothesis": "hypothesis", "exploratory": "exploratory query"}


def fmt_value(f: Finding) -> str:
    v = f.value
    if v is None:
        return "n/a (not established)"
    if isinstance(v, str):
        return v
    if f.fmt == "pct":
        s = f"{v * 100:.1f}%"
        if s in ("-0.0%",):              # a tiny negative change rounds to zero: never show a signed zero
            s = "0.0%"
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


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\u00a0", " ")).strip().lower()


def _strip_allowed(text: str) -> str:
    t = WPH.sub("", PH.sub("", text))
    return ALLOW.sub("", t)


def validate(answer: dict[str, Any], store: EvidenceStore, known_codes: set[str] | None = None,
             web: dict[str, dict] | None = None) -> list[str]:
    errs = []
    if not isinstance(answer, dict) or not answer.get("headline") or "body" not in answer:
        return ["answer must have 'headline' and 'body'"]
    texts = {"headline": answer["headline"], "body": answer["body"],
             **{f"claims[{i}]": c.get("text", "") for i, c in enumerate(answer.get("claims", []))},
             **{f"assumptions[{i}]": a for i, a in enumerate(answer.get("assumptions", []))},
             **{f"limitations[{i}]": a for i, a in enumerate(answer.get("limitations", []))},
             **{f"charts[{i}].title": (c or {}).get("title", "") for i, c in enumerate(answer.get("charts", []) or [])}}
    for where, t in texts.items():
        for wid in WPH.findall(t or ""):
            if wid not in (web or {}):
                errs.append(f"{where}: {{{wid}}} is not an external source fetched in this conversation")
        for fid, _ in PH.findall(t or ""):
            if fid not in store:
                errs.append(f"{where}: placeholder {{{fid}}} does not refer to a finding from this session")
        rest = _strip_allowed(t or "")
        bad = re.findall(r"[^\s]*\d[^\s]*", rest)
        if bad:
            errs.append(f"{where}: numbers must come from findings via placeholders; found literal(s) {bad[:5]}")
        words = NUMBER_WORDS.findall(ALLOWED_WORD_USES.sub("", PH.sub("", t or "")))
        if words:
            errs.append(f"{where}: quantities in words are not allowed (use findings): {words[:5]}")
        uni = _numeric_chars(PH.sub("", t or ""))
        if uni:
            errs.append(f"{where}: non-ASCII numeric characters are not allowed: {uni[:5]}")
        if known_codes:     # a placeholder must not be cited in a sentence about a different airport
            for sent in re.split(r"(?<=[.!?;])\s+|\n", t or ""):
                fids = [f for f, _ in PH.findall(sent) if f in store]
                codes = _codes_in(PH.sub("", sent), known_codes)
                for fid in fids:
                    subj = store.get(fid).subject.get("airport_code")
                    if subj and codes and subj not in codes:
                        errs.append(f"{where}: {fid} is about {subj} but the sentence names {sorted(codes)}")
    for i, c in enumerate(answer.get("charts", []) or []):
        if not isinstance(c, dict) or not isinstance(c.get("findings"), list) or not c["findings"]:
            errs.append(f"charts[{i}]: a chart needs findings:[F#, ...] (values are taken from the evidence store)")
            continue
        for fid in c["findings"]:
            if fid not in store:
                errs.append(f"charts[{i}]: {fid} is not a finding from this session")
    for i, c in enumerate(answer.get("claims", [])):
        kind = c.get("kind")
        if kind not in ("fact", "inference", "hypothesis", "external"):
            errs.append(f"claims[{i}]: kind must be fact|inference|hypothesis|external")
        if kind == "external":
            src, quote = c.get("source"), c.get("quote") or ""
            if src not in (web or {}):
                errs.append(f"claims[{i}]: external claims need source = a W# fetched with fetch_page in this conversation")
            elif not quote.strip() or len(quote) > 600:
                errs.append(f"claims[{i}]: external claims need a verbatim quote (≤600 chars) from {src}")
            elif _norm(quote) not in _norm(web[src]["text"]):
                errs.append(f"claims[{i}]: the quote is not a verbatim excerpt of {src} ({web[src]['url']})")
            if PH.search(c.get("text", "")):
                errs.append(f"claims[{i}]: external claims must not cite internal findings; use a fact/inference claim")
            continue
        sup = c.get("support") or []
        if kind in ("fact", "inference") and not sup:
            errs.append(f"claims[{i}]: a {kind} must cite at least one finding in 'support'")
        if kind == "hypothesis" and PH.search(c.get("text", "")):
            errs.append(f"claims[{i}]: hypotheses must not carry quantities; cite findings in a fact/inference instead")
        for fid in sup:
            if fid not in store:
                errs.append(f"claims[{i}]: support {fid} is not a finding from this session")
    return errs


def render(answer: dict[str, Any], store: EvidenceStore, known_codes: set[str] | None = None,
           web: dict[str, dict] | None = None) -> dict[str, Any]:
    web = web or {}
    errs = validate(answer, store, known_codes, web)
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
        if attr == "name":                    # metric name only (no subject / period)
            return f.label.split(" \u2014 ")[0]
        if attr == "period":
            return f.window.get("label", "")
        if attr == "class":
            return f.epistemic_class
        if attr == "definition":
            return f.definition
        return "; ".join(s.label() for s in f.sources)

    used_w: list[str] = []

    def wsub(m):
        it = web[m.group(1)]
        used_w.append(it["id"])
        return f"[{it['title']}]({it['url']})"

    def wsub_marked(m):
        it = web[m.group(1)]
        used_w.append(it["id"])
        return f"\u27e6{it['id']}|{it['domain'] or it['title']}\u27e7"

    def r(t):
        return WPH.sub(wsub, PH.sub(sub, t or ""))

    def rm(t):               # same text, but values carry their finding id for the UI: ⟦F12|20.6%⟧
        def subm(m):
            v = sub(m)
            return f"\u27e6{m.group(1)}|{v}\u27e7" if m.group(2) in (None, "value") else v
        return WPH.sub(wsub_marked, PH.sub(subm, t or ""))
    lines = [f"## {r(answer['headline'])}", "", r(answer["body"])]
    claims = answer.get("claims", [])
    if claims:
        lines += ["", "**Findings and reasoning**"]
        for c in claims:
            if c["kind"] == "external":
                it = web[c["source"]]
                used_w.append(it["id"])
                lines.append(f"- *External source ({it['domain']}, retrieved {it['retrieved_at'][:10]})*: {r(c['text'])} "
                             f"\u2014 \u201c{c['quote'].strip()}\u201d [{it['id']}]({it['url']})")
                continue
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
    wids = list(dict.fromkeys(used_w))
    if wids:
        lines += ["", "**External sources (web; not part of the internal datasets)**"] + [
            f"- {w}: [{web[w]['title']}]({web[w]['url']}) \u2014 {web[w]['domain']}, retrieved {web[w]['retrieved_at']}"
            for w in wids]
    charts = [c for c in answer.get("charts", []) or [] if isinstance(c, dict)]
    ids = list(dict.fromkeys(ids + [f for c in charts for f in c["findings"]]))
    structured = {"headline": r(answer["headline"]), "body": rm(answer["body"]),
                  "claims": [{"kind": c["kind"], "text": rm(c["text"]), "support": c.get("support") or [],
                              **({"source": c["source"], "quote": c["quote"].strip()} if c["kind"] == "external" else {})}
                             for c in claims],
                  "external": [{k: web[w][k] for k in ("id", "title", "url", "domain", "retrieved_at")} for w in wids],
                  "assumptions": [rm(a) for a in answer.get("assumptions", [])],
                  "limitations": [rm(x) for x in answer.get("limitations", [])],
                  "caveats": list(dict.fromkeys(c for f in expanded for c in f.caveats)),
                  "methodology": {f.metric_id: f.definition for f in expanded},
                  "evidence": list(dict.fromkeys([f.id for f in expanded] + ids)),
                  "charts": charts}
    return {"markdown": "\n".join(lines), "cited_findings": ids, "structured": structured}
