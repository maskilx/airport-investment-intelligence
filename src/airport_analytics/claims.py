"""Typed claims: does the cited evidence support the KIND of statement being made? (docs/10 §3)

render.validate guarantees *traceability*: every number in the answer comes from a finding. This module adds *semantic
validity*:

  kind        | requirement (deterministic)                                             | wording allowed
  ------------|-------------------------------------------------------------------------|------------------------------
  fact        | ≥1 current finding; every {F#} in the text is in support                 | neutral statement of values
  comparison  | findings[≥2] with the same metric+params, unit, class, period (or        | code writes the relation;
              | periods_differ acknowledged); `relation` verified against the values    | model text adds no direction
  ranking     | findings from one rank/screen operation; code writes the rank, the set  | judgement only for screens
              | size and (screens) the rank under every weighting scenario              |
  inference   | ≥1 finding; no causal, financial, capacity-need or comparative wording  | interpretation
  hypothesis  | ≥1 indicator finding AND ≥1 competing explanation (`alternatives`)      | causal / capacity language
  financial   | findings of class financial_model (none exist: stage C not built)       | → always rejected for now
  external    | W# + verbatim quote (render.quote_found)                                | attributed

Prose outside claims (headline, body) and assumptions/limitations are gated by the same vocabulary rules:
  * certainty words are never allowed;
  * financial, causal, capacity-need and judgement terms in limitations or assumptions need a negation or
    insufficiency marker in the same sentence;
  * a year may appear only if it is a period of a cited finding (closes "more gates by 2035").
The vocabulary gate is defence in depth (a paraphrase can evade a lexicon). The structural checks are the guarantee:
relations, ranks, compatibility, staleness and evidence classes are all checked by code.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .evidence import EvidenceStore, Finding

_W = lambda p: re.compile(r"\b(?:" + p + r")\b", re.I)
LEX = {
    "certainty": _W(r"guarantee[sd]?|guaranteeing|certain(?:ly)?|definitely|undoubtedly|assured(?:ly)?|risk[- ]free|"
                    r"no risk|sure to|surely|proven|proves?|bound to|inevitabl[ey]|without (?:a )?doubt"),
    "financial": _W(r"profit\w*|roi|returns? on (?:investment|capital|equity)|irr|npv|net present value|payback|ebitda|"
                    r"cash[- ]?flows?|revenues?|margins?|valuations?|lucrative|money|investor returns?|"
                    r"financial returns?|internal rate of return|break[- ]?even|economic returns?|"
                    r"pays? (?:back|off|for itself)|paid (?:back|off)|paying (?:back|off)|cost of capital|"
                    r"returns? (?:to|for) (?:investors?|equity|the investor)|earn(?:s|ing)?|financially|value[- ]accretive|"
                    r"cash cow|money[- ]maker"),
    "causal": _W(r"because|due to|caused by|causes?|causing|driven by|drives|driving|leads? to|led to|"
                 r"results? (?:in|from)|resulting in|owing to|attributable to|explains?|explained by|therefore|thus|"
                 r"hence|consequently|as a result"),
    "capacity_need": _W(r"gates?|square f(?:ee|oo)t|sq\.? ?ft|terminal capacity|capacity (?:shortfall|gap|deficit)s?|"
                        r"shortage|bottlenecks?|(?:needs?|requires?|requiring|warrants?|justif\w*) (?:an? )?"
                        r"(?:new |additional |more )?(?:expansion|terminal|capacity|gates?)|unmet demand|"
                        r"pent[- ]up demand|spill(?:ed|age)?|denied demand|over capacity|at capacity|"
                        r"capacity[- ]constrained|congested|overcrowded|saturated"),
    "judgement": _W(r"strong(?:est)? candidates?|promising|attractive|compelling|undervalued|best bet|"
                    r"best (?:opportunit\w+|investments?)|should (?:invest|expand|build)"),
    "comparative": _W(r"higher|lower|greater|fewer|larger|smaller|bigger|exceed(?:s|ed|ing)?|outpac\w+|surpass\w*|"
                      r"than|versus|vs\.?"),
    "ranking": _W(r"highest|lowest|largest|smallest|biggest|best|worst|tops?|bottom|leads|leading|ranks?|ranked|"
                  r"ranking|number one|first place"),
}
NEGATION = _W(r"not|no|never|cannot|can't|isn't|aren't|doesn't|without|unknown|unavailable|insufficient|"
              r"unmodell?ed|excluded|lacks?|absent|beyond|outside|neither|nor")
RANK_OPS = ("rank", "screen")
RELATIONS = ("higher", "lower", "similar", "highest", "lowest")
SIMILAR_REL_TOL = 0.05            # "similar" = within 5% of the larger magnitude (documented, not tuned)
PH = re.compile(r"\{(F\d+)(?:\.\w+)?\}")
YEAR = re.compile(r"\b(?:FY|CY)\s?((?:19|20)?\d\d)\b|\b((?:19|20)\d\d)\b")

# kind -> lexicon categories that are NOT allowed in its text
FORBIDDEN = {
    "prose": ("certainty", "financial", "causal", "capacity_need", "judgement", "comparative"),
    "fact": ("certainty", "financial", "causal", "capacity_need", "judgement", "comparative"),
    "inference": ("certainty", "financial", "causal", "capacity_need", "comparative"),
    "comparison": ("certainty", "financial", "causal", "capacity_need", "judgement", "comparative", "ranking"),
    "ranking": ("certainty", "financial", "causal", "capacity_need", "comparative"),
    "hypothesis": ("certainty", "financial"),
    "external": ("certainty",),
    "caveat": ("certainty",),
}
NEEDS_NEGATION = ("financial", "causal", "capacity_need", "judgement")
HINT = {
    "certainty": "certainty language is never supported by this evidence",
    "financial": "financial claims need a project-economics model with analyst assumptions (not built: stage C); "
                 "say profitability is not established",
    "causal": "causal language belongs in a hypothesis claim with competing explanations",
    "capacity_need": "terminal/capacity-need language needs intervention evidence; use a hypothesis claim",
    "judgement": "investment judgements must be inferences grounded in a screen/rank finding",
    "comparative": "comparisons must be a comparison claim (findings + relation); code writes the direction",
    "ranking": "rank statements must be a ranking claim citing rank/screen findings",
}


def _hits(text: str, cats) -> list[tuple[str, str]]:
    t = PH.sub(" ", text or "")
    return [(c, m.group(0)) for c in cats for m in [LEX[c].search(t)] if m]


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if s.strip()]


def _is_rank_finding(f: Finding) -> bool:
    return (f.execution or {}).get("op") in RANK_OPS and "rank" in f.subject


def _subject(f: Finding) -> str:
    s = f.subject
    if s.get("airport_code"):
        return s["airport_code"]
    if isinstance(s.get("entity_set"), list):
        return ", ".join(map(str, s["entity_set"]))
    parts = f.label.split(" — ")
    return parts[1] if len(parts) > 1 else f.id


def _allowed_years(store: EvidenceStore, fids: set[str]) -> set[str]:
    out: set[str] = set()
    for fid in fids:
        if fid not in store:
            continue
        f = store.get(fid)
        blob = " ".join([f.label, json.dumps(f.window, default=str), " ".join(p for s in f.sources for p in s.periods),
                         json.dumps((f.execution or {}).get("spec", {}).get("window") or {}, default=str),
                         json.dumps((f.execution or {}).get("spec", {}).get("metrics") or [], default=str)])
        for a, b in YEAR.findall(blob):
            y = a or b
            out.add(y if len(y) == 4 else "20" + y)
    return out


def _check_years(where: str, text: str, allowed: set[str]) -> list[str]:
    bad = []
    for a, b in YEAR.findall(PH.sub(" ", text or "")):
        y = a or b
        y = y if len(y) == 4 else "20" + y
        if y not in allowed:
            bad.append(y)
    return [f"{where}: year(s) {sorted(set(bad))} are not periods of any cited finding (a year is a claim too: cite "
            f"the finding whose period it is, or use {{F#.period}})"] if bad else []


def check_vocab(where: str, text: str, kind: str, rank_ok: bool = False) -> list[str]:
    cats = list(FORBIDDEN[kind])
    if kind in ("prose", "fact", "inference") and not rank_ok:
        cats.append("ranking")
    if kind == "inference" and not rank_ok:
        cats.append("judgement")
    errs = []
    if kind == "caveat":
        for s in _sentences(text):
            for c, w in _hits(s, NEEDS_NEGATION):
                if not NEGATION.search(s):
                    errs.append(f"{where}: '{w}' ({c}) in a caveat must be stated as not established "
                                f"(e.g. 'X is not modelled'); {HINT[c]}")
    return errs + [f"{where}: '{w}' is not allowed in a {kind} ({HINT[c]})" for c, w in _hits(text, cats)]


def _compat(fs: list[Finding], acknowledged: bool) -> list[str]:
    errs = []
    a = fs[0]
    for f in fs[1:]:
        if f.metric_id != a.metric_id:
            errs.append(f"{a.id} and {f.id} measure different things ({a.metric_id} vs {f.metric_id})")
        if f.unit != a.unit:
            errs.append(f"{a.id} and {f.id} have different units ({a.unit!r} vs {f.unit!r})")
        if f.epistemic_class != a.epistemic_class:
            errs.append(f"{a.id} is {a.epistemic_class} but {f.id} is {f.epistemic_class}")
        if f.window.get("label") != a.window.get("label") and not acknowledged:
            errs.append(f"{a.id} and {f.id} cover different periods ({a.window.get('label')} vs {f.window.get('label')}): "
                        "compare over a common period, or set periods_differ: true to state both")
    subj = [_subject(f) for f in fs]
    if len(set(subj)) != len(subj):
        errs.append(f"comparison subjects must differ (got {subj})")
    return errs


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= SIMILAR_REL_TOL * max(abs(a), abs(b), 1e-12)


def _relation_holds(rel: str, vals: list[float]) -> str | None:
    """None if the relation holds; otherwise why not. A difference inside the similarity band is not a direction:
    calling 20.6% 'higher' than 20.5% is true and misleading, so it must be stated as 'similar'."""
    v0, rest = vals[0], vals[1:]
    if rel == "similar":
        return None if all(_close(v0, v) for v in rest) else "the values differ by more than the similarity band"
    ok = all(v0 > v for v in rest) if rel in ("higher", "highest") else all(v0 < v for v in rest)
    if not ok:
        return f"the values do not support '{rel}'"
    nearest = min(rest, key=lambda v: abs(v0 - v))
    if _close(v0, nearest):
        return f"the difference is within {SIMILAR_REL_TOL:.0%}: use relation 'similar' (or compare fewer subjects)"
    return None


def validate_claim(i: int, c: dict, store: EvidenceStore) -> list[str]:
    where = f"claims[{i}]"
    kind = c.get("kind")
    text = c.get("text", "") or ""
    sup = list(c.get("support") or []) + list(c.get("findings") or [])
    errs: list[str] = []
    known = [s for s in sup if s in store]
    fs = [store.get(s) for s in known]
    rank_ok = any(_is_rank_finding(f) for f in fs)
    if kind == "fact":
        missing = [p for p in PH.findall(text) if p not in (c.get("support") or [])]
        if missing:
            errs.append(f"{where}: placeholders {missing} must also be listed in support")
        errs += check_vocab(where, text, "fact", rank_ok)
    elif kind == "inference":
        errs += check_vocab(where, text, "inference", rank_ok)
    elif kind == "comparison":
        ids = c.get("findings") or []
        rel = c.get("relation")
        if len(ids) < 2:
            errs.append(f"{where}: a comparison needs findings: [F#, F#, ...] (the first is the subject of the relation)")
        elif rel not in RELATIONS:
            errs.append(f"{where}: relation must be one of {list(RELATIONS)}")
        elif all(s in store for s in ids):
            cf = [store.get(s) for s in ids]
            if any(not isinstance(f.value, (int, float)) for f in cf):
                errs.append(f"{where}: every compared finding needs a numeric value")
            else:
                errs += [f"{where}: {e}" for e in _compat(cf, bool(c.get("periods_differ")))]
                if rel in ("higher", "lower", "similar") and len(cf) != 2:
                    errs.append(f"{where}: '{rel}' compares exactly two findings; use highest/lowest for a set")
                elif (why := _relation_holds(rel, [f.value for f in cf])):
                    errs.append(f"{where}: {why} ({', '.join(f'{f.id}={f.value:.6g}' for f in cf)})")
        if PH.search(text):
            errs.append(f"{where}: comparison text must not carry values; code renders them from the findings")
        errs += check_vocab(where, text, "comparison")
    elif kind == "ranking":
        ids = c.get("findings") or []
        if not ids:
            errs.append(f"{where}: a ranking claim needs findings: [F#] from a rank or screen result")
        cf = [store.get(s) for s in ids if s in store]
        if any(not _is_rank_finding(f) for f in cf):
            errs.append(f"{where}: {[f.id for f in cf if not _is_rank_finding(f)]} do not come from a rank/screen "
                        "operation; a rank cannot be asserted from individual values")
        elif len({json.dumps((f.execution or {}).get("spec"), sort_keys=True, default=str) for f in cf}) > 1:
            errs.append(f"{where}: findings come from different rank/screen operations")
        screen = any((f.execution or {}).get("op") == "screen" for f in cf)
        errs += check_vocab(where, text, "ranking")
        if not screen:                    # an investment judgement needs the investment screen, not any ranking
            errs += [f"{where}: '{w}' is not allowed here ({HINT[k]})" for k, w in _hits(text, ["judgement"])]
        if PH.search(text):
            errs.append(f"{where}: ranking text must not carry values; code renders the rank from the finding")
    elif kind == "hypothesis":
        alts = [a for a in c.get("alternatives") or [] if isinstance(a, str) and a.strip()]
        if not c.get("support"):
            errs.append(f"{where}: a hypothesis must cite the indicator findings it is based on (support)")
        if not alts:
            errs.append(f"{where}: a hypothesis needs at least one competing explanation (alternatives)")
        for k, a in enumerate(alts):
            errs += check_vocab(f"{where}.alternatives[{k}]", a, "hypothesis")
        errs += check_vocab(where, text, "hypothesis")
    elif kind == "financial":
        if not fs or any(f.epistemic_class != "financial_model" for f in fs):
            errs.append(f"{where}: financial claims require findings from a project-economics model "
                        "(class financial_model), which needs analyst capacity, cost and revenue-rights assumptions. "
                        "None exists here: state that profitability is not established, or ask for the assumptions.")
    elif kind == "external":
        errs += check_vocab(where, text, "external")
    if kind != "external":
        for s in sup:
            if s not in store:
                errs.append(f"{where}: {s} is not a finding from this session")
    return errs


def validate_answer(answer: dict[str, Any], store: EvidenceStore) -> list[str]:
    errs: list[str] = []
    claims = [c for c in answer.get("claims", []) or [] if isinstance(c, dict)]
    cited = {p for t in (answer.get("headline"), answer.get("body")) for p in PH.findall(t or "")}
    for c in claims:
        cited |= set(PH.findall(c.get("text", "") or "")) | set(c.get("support") or []) | set(c.get("findings") or [])
    for c in answer.get("charts", []) or []:
        if isinstance(c, dict):
            cited |= set(c.get("findings") or [])
    rank_ok = any(f in store and _is_rank_finding(store.get(f)) for f in cited)
    years = _allowed_years(store, cited)
    for where in ("headline", "body"):
        errs += check_vocab(where, answer.get(where, ""), "prose", rank_ok)
        errs += _check_years(where, answer.get(where, ""), years)
    for key in ("assumptions", "limitations"):
        for k, t in enumerate(answer.get(key, []) or []):
            errs += check_vocab(f"{key}[{k}]", t, "caveat")
            errs += _check_years(f"{key}[{k}]", t, years)
    for i, c in enumerate(claims):
        errs += validate_claim(i, c, store)
        errs += _check_years(f"claims[{i}]", c.get("text", ""), years)
    for k, c in enumerate(answer.get("charts", []) or []):
        if isinstance(c, dict):
            errs += check_vocab(f"charts[{k}].title", c.get("title", ""), "prose", rank_ok)
            errs += _check_years(f"charts[{k}].title", c.get("title", ""), years)
    return errs


def expand(c: dict, store: EvidenceStore) -> dict:
    """Deterministic text for comparison and ranking claims (placeholders, rendered by render.sub)."""
    kind = c.get("kind")
    note = (c.get("text") or "").strip()
    if kind == "comparison":
        ids = c["findings"]
        fs = [store.get(i) for i in ids]
        name = "{" + ids[0] + ".name}"
        vals = "; ".join(f"{_subject(f)} {{{f.id}}}" + (f" ({{{f.id}.period}})" if c.get("periods_differ") else "")
                         for f in fs)
        a, others = _subject(fs[0]), ", ".join(_subject(f) for f in fs[1:])
        rel = {"higher": f"{a} is higher than {others}", "lower": f"{a} is lower than {others}",
               "similar": f"{a} and {others} are similar (within {SIMILAR_REL_TOL:.0%})",
               "highest": f"{a} is the highest of the compared airports", "lowest": f"{a} is the lowest of the compared airports"}[c["relation"]]
        per = "" if c.get("periods_differ") else f", {{{ids[0]}.period}}"
        txt = f"On {name}{per}: {rel} ({vals})."
        if c.get("periods_differ"):
            txt += " Periods differ, so the comparison is indicative."
        return {**c, "text": txt + (f" {note}" if note else ""), "support": list(ids)}
    if kind == "ranking":
        parts = []
        for i in c["findings"]:
            f = store.get(i)
            s = f.subject
            of = f" of {s['of']}" if s.get("of") else ""
            sc = s.get("scenario_ranks") or {}
            rob = ""
            if sc:
                lo, hi = min(sc.values()), max(sc.values())
                rob = (" in every weighting scenario" if lo == hi else
                       f"; across the weighting scenarios its rank ranges from {lo} to {hi}")
            scen = ((f.execution or {}).get("screening") or {}).get("scenario")
            main = f"; largest contribution: {s['main_contributor']}" if s.get("main_contributor") else ""
            parts.append(f"{_subject(f)} is ranked {s['rank']}{of} by {{{i}.name}}"
                         + (f" ({scen} scenario)" if scen else "") + rob + main)
        return {**c, "text": "; ".join(parts) + "." + (f" {note}" if note else ""), "support": list(c["findings"])}
    if kind == "hypothesis" and c.get("alternatives"):
        alts = "; ".join(a.strip().rstrip(".") for a in c["alternatives"] if a.strip())
        return {**c, "text": f"{c.get('text', '').strip()} Competing explanations: {alts}."}
    return c
