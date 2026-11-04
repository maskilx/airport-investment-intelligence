"""Missing-information handling (FDE behaviour): classify what a question needs before giving up on it.

check_information(need) answers, deterministically:
  case "exists"         - the catalog measures it: retrieve and continue (metric ids returned);
  case "derivable"      - computable from catalog metrics with `derive` / transforms (formula noted by the caller);
  case "proxy"          - not measured; catalog indicators are useful proxies (what they cannot establish is stated);
  case "external"       - a reputable public source exists outside the database (web research or a new adapter);
  case "not_measurable" - cannot be established from available measurements; partial analysis + next step;
  case "unknown"        - not recognised: the agent should check the catalog itself or ask what is meant.
The concept map lives in config/information_gaps.toml; every proxy id is validated against the metric catalog at load.
"""
from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from typing import Any

from airport_data.config import REPO_ROOT

from .semantic import METRICS

CASES = ("exists", "derivable", "proxy", "external", "not_measurable", "unknown")
DERIVABLE = {   # combinations that the deterministic engine can compute from catalog metrics
    "growth": ("passengers", "transform pct_change / cagr over two windows"),
    "change": ("passengers", "transform abs_change / pct_change"),
    "per capita": ("passengers", "derive ratio with cbsa_population"),
    "per enplanement": ("npias_need_per_enplanement", "catalog metric"),
    "forecast error": ("taf_enplanements", "op forecast_vs_actual"),
}


@lru_cache(maxsize=1)
def concepts() -> dict[str, dict]:
    cfg = tomllib.loads((REPO_ROOT / "config" / "information_gaps.toml").read_text())["concepts"]
    for cid, c in cfg.items():
        bad = [p for p in c.get("proxies", []) if p not in METRICS]
        if bad:
            raise ValueError(f"information_gaps.toml: {cid} lists unknown metric ids {bad}")
        if c["case"] not in CASES:
            raise ValueError(f"information_gaps.toml: {cid} has unknown case {c['case']}")
    return cfg


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def match_concepts(text: str) -> list[str]:
    t = f" {_norm(text)} "
    return [cid for cid, c in concepts().items() if any(f" {_norm(k)} " in t for k in c["keywords"])]


def catalog_matches(text: str, limit: int = 5) -> list[str]:
    toks = {w for w in _norm(text).split() if len(w) > 3}
    scored = []
    for m in METRICS.values():
        words = set(_norm(f"{m.id.replace('_', ' ')} {m.name}").split())
        s = len(toks & words)
        if s:
            scored.append((s, m.id))
    return [mid for _, mid in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def check(need: str, web_available: bool = False) -> dict[str, Any]:
    """Classify an information need. Never invents a value; returns metric ids, notes and the next step."""
    hits = match_concepts(need)
    if hits:
        c = concepts()[hits[0]]
        out = {"need": need, "concept": hits[0], "label": c["label"], "case": c["case"],
               "proxies": [{"metric": p, "name": METRICS[p].name} for p in c.get("proxies", [])],
               "proxy_note": c.get("proxy_note", ""), "cannot_establish": c.get("cannot_establish", ""),
               "needed": c.get("needed", []), "external_sources": c.get("external", []),
               "next_step": c.get("next_step", ""),
               "guidance": ("Run the proxy metrics, label them as proxies, state what they cannot establish, and give "
                            "the next step. Do not estimate the missing quantity.")}
        if c["case"] == "external" and web_available:
            out["guidance"] += (" Web research is available: fetch the primary source page and cite verbatim quotes "
                                "(a search snippet is not evidence).")
        return out
    t = _norm(need)
    for k, (metric, how) in DERIVABLE.items():
        if f" {k} " in f" {t} ":
            return {"need": need, "case": "derivable", "base_metric": metric, "how": how,
                    "guidance": "Compute it with the engine (transform/derive) and state the formula and windows."}
    cat = catalog_matches(need)
    if cat:
        return {"need": need, "case": "exists", "metrics": cat,
                "guidance": "Use describe_catalog on these ids, then run_analysis."}
    return {"need": need, "case": "unknown",
            "guidance": "Not recognised. Check describe_catalog; if still unclear, ask the user one focused question."}
