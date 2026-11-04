"""Assumption dependencies: which findings still hold under the conversation's current assumptions.

An assumption (A#) is analyst intent. It may carry a structured *binding* that code can check:
    {"metric": "long_haul_share", "param": "min_miles", "value": 2400}
    {"screen_option": "scenario", "value": "demand_only"}   (or "min_enplanements")

Rules (deterministic; docs/10 §3):
  1. Every finding records the A# ids active when it was produced (finding.assumptions).
  2. A bound assumption invalidates every *current* finding that depends on the bound parameter with a different
     value — whenever it was computed (including findings that used the default before the analyst said otherwise,
     and findings computed later in contradiction of it).
  3. Superseding or retracting an assumption invalidates the findings produced under it: if it was bound, only those
     that depend on the bound parameter; if it was unbound (free text), all of them (coarse but safe: a re-run is cheap,
     a silently wrong citation is not).
  4. Staleness propagates to derived findings (derive inputs).
A stale finding stays inspectable (provenance, replay) but cannot be cited in an answer or chart (render.validate).
"""
from __future__ import annotations

import re
from typing import Any

from airport_analytics.evidence import EvidenceStore, Finding
from airport_analytics.semantic import METRICS

SCREEN_OPTIONS = {"scenario", "min_enplanements"}
_MID = re.compile(r"^([a-z0-9_]+)\((.*)\)$")


def metric_params(metric_id: str) -> tuple[str, dict[str, str]]:
    """'long_haul_share(min_miles=3000,scope=passenger)' -> ('long_haul_share', {'min_miles': '3000', ...})."""
    m = _MID.match(metric_id or "")
    if not m:
        return metric_id, {}
    params = dict(kv.split("=", 1) for kv in m.group(2).split(",") if "=" in kv)
    return m.group(1), params


def validate_binds(b: Any) -> tuple[dict | None, str | None]:
    if b is None:
        return None, None
    if not isinstance(b, dict):
        return None, "binds must be an object"
    if "screen_option" in b:
        opt = b["screen_option"]
        if opt not in SCREEN_OPTIONS:
            return None, f"screen_option must be one of {sorted(SCREEN_OPTIONS)}"
        if opt == "scenario":
            from airport_analytics.analysis import load_screening
            if b.get("value") not in load_screening()["scenarios"]:
                return None, f"unknown scenario {b.get('value')!r}"
            return {"screen_option": opt, "value": b["value"]}, None
        try:
            return {"screen_option": opt, "value": float(b.get("value"))}, None
        except (TypeError, ValueError):
            return None, "min_enplanements must be a number"
    mid, pname = b.get("metric"), b.get("param")
    m = METRICS.get(mid)
    if not m:
        return None, f"unknown metric {mid!r}"
    p = next((p for p in m.params if p.name == pname), None)
    if not p:
        return None, f"metric {mid} has no parameter {pname!r} (params: {[p.name for p in m.params]})"
    v = b.get("value")
    if p.kind == "int":
        try:
            v = int(v)
        except (TypeError, ValueError):
            return None, f"{pname} must be an integer"
        if (p.lo is not None and v < p.lo) or (p.hi is not None and v > p.hi):
            return None, f"{pname} must be within [{p.lo}, {p.hi}]"
    elif p.choices:
        match = next((c for c in p.choices if str(c) == str(v)), None)
        if match is None:
            return None, f"{pname} must be one of {list(p.choices)}"
        v = match
    return {"metric": mid, "param": pname, "value": v}, None


def depends(f: Finding, b: dict) -> tuple[bool, Any]:
    """(does finding f depend on the bound parameter, with which value)."""
    if "screen_option" in b:
        ex = f.execution or {}
        if ex.get("op") != "screen":
            return False, None
        opts = (ex.get("spec") or {}).get("options") or {}
        if b["screen_option"] == "scenario":
            return True, opts.get("scenario", "base")
        from airport_analytics.analysis import load_screening
        return True, float(opts.get("min_enplanements", load_screening()["gate"]["min_enplanements"]))
    base, params = metric_params(f.metric_id)
    if base != b["metric"] or b["param"] not in params:
        return False, None
    return True, params[b["param"]]


def _differs(have: Any, want: Any) -> bool:
    try:
        return float(have) != float(want)
    except (TypeError, ValueError):
        return str(have) != str(want)


def _label(b: dict) -> str:
    return (f"screen {b['screen_option']}" if "screen_option" in b else f"{b['metric']}.{b['param']}") + f" = {b['value']}"


def mark(f: Finding, reason: str) -> bool:
    if f.status == "stale":
        return False
    f.status, f.status_reason = "stale", reason
    return True


def propagate(store: EvidenceStore) -> list[str]:
    out, changed = [], True
    while changed:
        changed = False
        for f in store.current():
            bad = [i for i in f.inputs if i in store and store.get(i).status == "stale"]
            if bad and mark(f, f"derived from stale finding(s) {', '.join(bad)}"):
                out.append(f.id)
                changed = True
    return out


def conflicts_with_active(f: Finding, active: list[dict]) -> str | None:
    for a in active:
        b = a.get("binds")
        if b:
            dep, have = depends(f, b)
            if dep and _differs(have, b["value"]):
                return f"computed with {_label(dict(b, value=have))}; active assumption {a['id']} sets {_label(b)}"
    return None


def tag_new(new: list[Finding], active: list[dict], store: EvidenceStore) -> list[dict]:
    """Rule 1 + rule 2 at creation time. Returns [{id, reason}] for findings born stale."""
    out = []
    ids = [a["id"] for a in active]
    for f in new:
        f.assumptions = list(ids)
        why = conflicts_with_active(f, active)
        if why and mark(f, why):
            out.append({"id": f.id, "reason": why})
    out += [{"id": i, "reason": store.get(i).status_reason} for i in propagate(store)]
    return out


def on_change(store: EvidenceStore, old: dict | None, new: dict | None) -> list[dict]:
    """Rules 2–4 when an assumption is set (new), superseded (old -> new) or retracted (old)."""
    out = []
    if old:
        for f in store.current():
            if old["id"] not in f.assumptions:
                continue
            ob = old.get("binds")
            if ob and not depends(f, ob)[0]:
                continue
            why = (f"produced under assumption {old['id']}, which is now {old['status']}"
                   + (f" (replaced by {old.get('superseded_by')})" if old.get("superseded_by") else ""))
            if mark(f, why):
                out.append({"id": f.id, "reason": why})
    if new and new.get("binds"):
        for f in store.current():
            why = conflicts_with_active(f, [new])
            if why and mark(f, why):
                out.append({"id": f.id, "reason": why})
    out += [{"id": i, "reason": store.get(i).status_reason} for i in propagate(store)]
    return out


def binds_label(b: dict | None) -> str:
    return _label(b) if b else ""
