"""Passenger Growth Opportunity Screen — stage A of the three-stage method (config/screening.toml, docs/10 §4).

It ranks where forecast and realized passenger growth and market income are strongest. It does NOT establish that a
terminal is the binding constraint (stage B: intervention suitability) or that a project pays (stage C: economics).

score = Σ_i w_i · S_i(x_i),  S = clip((g(x) − g(lo)) / (g(hi) − g(lo)), 0, 1) · 100,  g = identity or log10.
Additive by construction: contributions sum exactly to the score. No imputation, no reweighting:
an airport missing any input is listed as not scored with the reason. Feasibility facts are FLAGS,
shown beside the rank, never folded into the number.
"""
from __future__ import annotations

import math
import re
from typing import Any

from .evidence import InsufficientData, InvalidSpec, SourceRef


def _scale(x: float, comp: dict) -> float:
    lo, hi = float(comp["lo"]), float(comp["hi"])
    if comp["scale"] == "log10":
        if x <= 0:
            return 0.0
        x, lo, hi = math.log10(x), math.log10(lo), math.log10(hi)
    return max(0.0, min(1.0, (x - lo) / (hi - lo))) * 100


# Evidence ladder for curated constraint records (docs/10 §1.3). Only primary/secondary evidence drives a flag;
# weaker records are shown as reported-but-unverified, never hidden and never treated as fact.
EVIDENCE_LEVELS = ("primary", "secondary", "snippet", "unverified")
FLAG_LEVELS = ("primary", "secondary")
STRICT_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*$")   # "76" or "76-78", nothing else


def evidence_level(verification: str) -> str:
    v = (verification or "").strip().lower()
    if v.startswith("verified:primary"):
        return "primary"
    if v.startswith("verified:secondary"):
        return "secondary"
    if v.startswith("verified:search_snippet") or v.startswith("verified:snippet"):
        return "snippet"
    return "unverified"


def strict_range(value: str) -> tuple[float, float] | None:
    """A capacity value is usable only if the WHOLE field is a number or a numeric range. Free text such as
    '12.2 (12.5 if ...)' is not parsed for numbers: it is reported as unusable."""
    m = STRICT_NUM.match(str(value or ""))
    if not m:
        return None
    lo = float(m.group(1))
    return lo, float(m.group(2) or lo)


def constraint_records(ctx, as_of: str) -> list[dict]:
    """Curated constraints with evidence level and effectiveness at `as_of` (ISO date)."""
    rows = ctx.engine.con.execute("""SELECT airport_iata, category, item, value, unit, effective_from, effective_to,
        status, verification, source_url FROM curated_constraint""").fetchall()
    out = []
    for code, cat, item, val, unit, ef, et, status, ver, url in rows:
        ef_s, et_s = str(ef or "").strip(), str(et or "").strip()
        lvl = evidence_level(ver)
        # dates decide (the status column describes the record today, not at as_of); status only fills a missing end
        if et_s and et_s[:len(as_of)] < as_of[:len(et_s)]:
            eff = "ended"
        elif ef_s and ef_s[:len(as_of)] > as_of[:len(ef_s)]:
            eff = "not_yet"
        elif not et_s and (status or "").lower() in ("superseded", "expired") and cat in ("regulatory_cap", "curfew"):
            eff = "ended"
        else:
            eff = "in_effect"
        out.append({"airport": code, "category": cat, "item": item, "value": val, "unit": unit, "effective_from": ef_s,
                    "effective_to": et_s, "status": status, "evidence": lvl, "effective": eff, "source_url": url})
    return out


def _verified_imc_rates(recs: list[dict]) -> tuple[dict[str, float], list[dict]]:
    """Highest verified instrument-condition rate per airport (best configuration: the conservative choice for a
    'schedule exceeds capacity' flag), from primary/secondary records with a strictly numeric value."""
    out: dict[str, float] = {}
    rejected = []
    for r in recs:
        if r["category"] != "capacity_rate" or "instrument" not in (r["item"] or "").lower() or r["effective"] != "in_effect":
            continue
        rng = strict_range(r["value"])
        if r["evidence"] not in FLAG_LEVELS or rng is None or "operations/hour" not in (r["unit"] or ""):
            rejected.append({"airport": r["airport"], "item": r["item"], "evidence": r["evidence"],
                             "reason": "evidence below secondary" if r["evidence"] not in FLAG_LEVELS
                             else "value is not a strict number/range in operations/hour"})
            continue
        out[r["airport"]] = max(out.get(r["airport"], 0.0), rng[1])
    return out, rejected


def _hours_above(ctx, aid: int, rate: float, months: list[str]) -> tuple[float, int]:
    e = ctx.engine
    sql = f"""WITH h AS (SELECT flight_date, hr, count(*) n FROM (
                SELECT flight_date, crs_dep_hour hr FROM v_ontime_flight WHERE origin_airport_id = {int(aid)}
                  AND cancelled = 0 AND period_month IN ({e.month_list(months)})
                UNION ALL SELECT flight_date, crs_arr_hour FROM v_ontime_flight WHERE dest_airport_id = {int(aid)}
                  AND cancelled = 0 AND period_month IN ({e.month_list(months)})) GROUP BY ALL)
              SELECT count(*) FILTER (WHERE n > {rate}) / count(*), count(*) FROM h"""
    share, n = e.con.execute(sql).fetchone()
    return share, n


def _anchor(c: dict, v: float) -> str:
    """Anchor values in the reader's units: growth rates as %, income as $, counts with separators."""
    v = float(v)
    if "income" in c["id"]:
        return f"${v:,.0f}"
    if max(abs(float(c["lo"])), abs(float(c["hi"]))) <= 1:
        return f"{v:+.0%}"
    return f"{v:,.0f}"


def score_definition(cfg: dict, w: list[float], gate: float) -> str:
    comps = cfg["component"]
    parts = "; ".join(f"{c['label']}: weight {wi:g}, {c['scale']} scale {_anchor(c, c['lo'])} → 0 points and {_anchor(c, c['hi'])} → 100 "
                      f"points (clipped)" for c, wi in zip(comps, w))
    return (f"Score = Σ weight × factor points (0-100). {parts}. Eligibility: at least {gate:,.0f} annual FAA "
            f"enplanements (latest calendar year); smaller airports are listed, not scored. An airport missing any "
            f"factor input is listed as not scored: no imputation and no reweighting. Gaps under "
            f"{float(cfg['ties']['points']):g} points are reported as ties. Model {cfg['model_version']}.")


def method_summary(cfg: dict | None = None) -> list[str]:
    """Deterministic, human-readable scoring method (rendered under every answer that cites a screen score)."""
    from .analysis import load_screening
    cfg = cfg or load_screening()
    comps, base = cfg["component"], cfg["scenarios"]["base"]
    out = [f"Purpose: ranks passenger growth opportunity (stage A). It does not establish that a terminal is the binding "
           f"constraint or that a project pays (model {cfg['model_version']}, config/screening.toml)."]
    for i, (c, wi) in enumerate(zip(comps, base), 1):
        out.append(f"Factor {i}, {c['label']}: weight {wi:.0%}; {c['scale']} scale, {_anchor(c, c['lo'])} → 0 points and "
                   f"{_anchor(c, c['hi'])} → 100 points; values outside are clipped.")
    out += [f"Score = Σ weight × factor points (0-100). Each airport's per-factor points are separate findings in the evidence.",
            f"Eligibility: at least {float(cfg['gate']['min_enplanements']):,.0f} annual FAA enplanements (latest calendar "
            f"year); smaller airports are listed as below scale, not scored.",
            "Missing data: an airport missing any factor input is listed as not scored. No imputation, no reweighting.",
            f"Ties: score gaps under {float(cfg['ties']['points']):g} points are reported as ties.",
            "Robustness: ranks are recomputed under the weight scenarios " + "; ".join(
                f"{n} ({', '.join(f'{x:.0%}' for x in ws)})" for n, ws in cfg["scenarios"].items()) + ".",
            "Flags (regulatory caps, curfews, airfield capacity, carrier concentration) are shown beside the score and "
            "never folded into it. Only primary or secondary evidence in effect at the as-of date raises a flag."]
    return out


def screen(spec: dict, ids: list[int], notes: dict, ctx) -> dict[str, Any]:
    from .analysis import _new, _per_airport, _round, load_screening
    cfg = load_screening()
    comps = cfg["component"]
    opts = spec.get("options") or {}
    scen_name = opts.get("scenario", "base")
    if scen_name not in cfg["scenarios"]:
        raise InvalidSpec(f"unknown scenario {scen_name}", allowed=list(cfg["scenarios"]))
    gate = float(opts.get("min_enplanements", cfg["gate"]["min_enplanements"]))
    # gate on latest CY enplanements
    g = _per_airport({"entities": spec["entities"], "window": {"t12": True}}, ids, notes, ctx, ["acais_enplanements"])
    enp = g["acais_enplanements"]
    eligible = [a for a in ids if enp.get(a) and enp[a].value is not None and enp[a].value >= gate]
    below = [{"airport": ctx.resolver.code(a), "enplanements": {"id": enp[a].id, "value": _round(enp[a].value)}}
             for a in ids if a not in eligible and enp.get(a) and enp[a].value]
    no_record = [ctx.resolver.code(a) for a in ids if not enp.get(a) or enp[a].value is None]   # unknown, not zero
    if not eligible:
        raise InsufficientData(f"no airport in the set meets the {gate:,.0f}-enplanement gate", below_scale=below)
    vals = _per_airport({"entities": spec["entities"]}, eligible, notes, ctx, [c["metric"] for c in comps])
    keys = list(vals)
    weights = {name: w for name, w in cfg["scenarios"].items()}
    scored, not_scored = [], []
    for aid in eligible:
        fs = [vals[k].get(aid) for k in keys]
        missing = [c["id"] for c, f in zip(comps, fs) if f is None or f.value is None]
        if missing:
            not_scored.append({"airport": ctx.resolver.code(aid), "missing_inputs": missing})
            continue
        s = [_scale(f.value, c) for c, f in zip(comps, fs)]
        scored.append((aid, fs, s))
    if not scored:
        raise InsufficientData("no eligible airport has all screening inputs", not_scored=not_scored)

    def total(svals, w):
        return sum(wi * si for wi, si in zip(w, svals))
    ranks_by_scen = {}
    for name, w in weights.items():
        order = sorted(scored, key=lambda t: -total(t[2], w))
        ranks_by_scen[name] = {t[0]: i + 1 for i, t in enumerate(order)}
    w = weights[scen_name]
    order = sorted(scored, key=lambda t: -total(t[2], w))
    # flags (constraints evaluated at an explicit as-of date, recorded for replay)
    from datetime import date
    as_of = str(opts.get("as_of") or date.today().isoformat())
    recs = constraint_records(ctx, as_of)
    imc, imc_rejected = _verified_imc_rates(recs)
    ot_months = ctx.engine.available("ontime_dep")[-12:]
    caps: dict[str, list[dict]] = {}
    for r in recs:
        if r["category"] in ("regulatory_cap", "curfew") and r["effective"] == "in_effect":
            caps.setdefault(r["airport"], []).append(r)
    ended = [{"airport": r["airport"], "item": r["item"], "effective_to": r["effective_to"]} for r in recs
             if r["category"] in ("regulatory_cap", "curfew") and r["effective"] != "in_effect"]
    conc = _per_airport({"entities": spec["entities"]}, [t[0] for t in scored], notes, ctx, ["top_carrier_share"])["top_carrier_share"]
    ctxv = _per_airport({"entities": spec["entities"]}, [t[0] for t in scored], notes, ctx,
                        ["npias_need_usd", {"id": "grants_awarded_usd", "window": {"fy_range": [2021, 2025]}}])
    table, findings = [], []
    tie_pts = float(cfg["ties"]["points"])
    prev = None
    for rank, (aid, fs, svals) in enumerate(order, 1):
        code = ctx.resolver.code(aid)
        sc = total(svals, w)
        contrib = [wi * si for wi, si in zip(w, svals)]
        # one calculated finding per factor: weight x anchored points, so "why this score" is inspectable
        cfs = []
        for c, x, wi, si, p in zip(comps, fs, w, svals, contrib):
            cfs.append(_new(ctx, metric_id=f"screen_contribution:{c['id']}", label=f"{c['label']}: points contributed — {code} ({scen_name})",
                            value=p, unit="points (anchored scale)", fmt="number", epistemic_class="calculated",
                            definition=f"weight {wi:g} × anchored factor score {si:.1f}/100 "
                                       f"({c['scale']} scale, {_anchor(c, c['lo'])} → 0 and {_anchor(c, c['hi'])} → 100, clipped)",
                            formula_version=cfg["model_version"], subject={"airport": aid, "airport_code": code,
                                                                         "component": c["id"]},
                            window=x.window, sources=list(x.sources), inputs=[x.id]))
        f = _new(ctx, metric_id=f"screen_score:{cfg['model_version']}", label=f"Passenger growth opportunity score — {code} ({scen_name})",
                 value=sc, unit="points (anchored scale)", fmt="number", epistemic_class="calculated",
                 definition=score_definition(cfg, w, gate),
                 formula_version=cfg["model_version"],
                 subject={"airport": aid, "airport_code": code, "rank": rank, "of": len(order),
                          "scenario_ranks": {n: ranks_by_scen[n][aid] for n in weights},
                          "main_contributor": comps[max(range(len(contrib)), key=lambda i: contrib[i])]["label"]},
                 window={"label": "see inputs"}, sources=[s for x in fs for s in x.sources],
                 caveats=[cfg["disclaimer"], "TAF component is an FAA forecast (unconstrained)."],
                 inputs=[x.id for x in cfs] + [x.id for x in fs])
        flags = []
        for r in caps.get(code, []):
            strong = r["evidence"] in FLAG_LEVELS
            flags.append({"flag": ("REGULATORY_CAP" if r["category"] == "regulatory_cap" else "CURFEW") if strong
                          else "REPORTED_CONSTRAINT_UNVERIFIED",
                          "detail": f"{r['item']} (effective {r['effective_from'] or 'n/a'} to {r['effective_to'] or 'open'})",
                          "evidence": r["evidence"], "source_url": r["source_url"],
                          "class": f"observed (curated, {r['evidence']} evidence)" if strong else "not_established"})
        if code in imc:
            share, nh = _hours_above(ctx, aid, imc[code], ot_months)
            fh = _new(ctx, metric_id="hours_above_imc_rate", label=f"Share of operating hours with reporting-carrier schedule > IMC rate — {code}",
                      value=share, unit="ratio", fmt="pct", epistemic_class="calculated",
                      definition=f"hours (date × local hour, ≥1 operated flight) where scheduled arr+dep of reporting carriers > {imc[code]:g} ops/h "
                                 f"(highest verified IMC rate); lower bound on total demand", formula_version="1",
                      subject={"airport": aid, "airport_code": code}, window={"label": f"{ot_months[0]}…{ot_months[-1]}"},
                      sources=ctx.engine.lineage("ontime_dep", ctx.engine.resolve_window({"months": ot_months}, "ontime_dep"))
                      + [SourceRef("curated_constraints", ["current"], [])],
                      caveats=["Lower bound: excludes international, non-reporting and GA traffic.",
                               f"Capacity rate: FAA Airport Capacity Profile (verified), {imc[code]:g} ops/h."])
            findings.append(fh.brief())
            thr = float(cfg["flags"].get("airfield_binding_hour_share", 0.05))
            flags.append({"flag": "AIRFIELD_BINDING" if share is not None and share >= thr else "AIRFIELD_HEADROOM_IMC",
                          "threshold_hour_share": thr,
                          "detail": {"id": fh.id, "value": _round(share)}, "class": "calculated (lower bound)"})
        else:
            flags.append({"flag": "AIRFIELD_UNKNOWN", "detail": "no verified FAA capacity rate", "class": "not_established"})
        cf = conc.get(aid)
        if cf and cf.value is not None and cf.value > cfg["flags"]["carrier_concentration_share"]:
            flags.append({"flag": "CARRIER_CONCENTRATION", "detail": {"id": cf.id, "value": _round(cf.value)},
                          "class": "calculated", "note": "hub tenant anchors leases but adds de-hubbing risk"})
        n_ = ctxv["npias_need_usd"].get(aid)
        gr = next(iter(v for k, v in ctxv.items() if k.startswith("grants")), {}).get(aid)
        tie = prev is not None and abs(prev - sc) < tie_pts
        prev = sc
        table.append({"rank": rank, "airport": code, "score": {"id": f.id, "value": round(sc, 1)},
                      "tied_with_previous": tie,
                      "components": {c["id"]: {"input": {"id": x.id, "value": _round(x.value)}, "points": round(p, 1),
                                               "points_id": cf.id}
                                     for c, x, p, cf in zip(comps, fs, contrib, cfs)},
                      "scenario_ranks": {n: ranks_by_scen[n][aid] for n in weights},
                      "flags": flags,
                      "capital_context": {"npias_need_usd": n_ and {"id": n_.id, "value": _round(n_.value)},
                                          "grants_awarded_fy21_25_usd": gr and {"id": gr.id, "value": _round(gr.value)}}})
        findings += [x.brief() for x in cfs]
        findings.append(f.brief())
    return {"op": "screen", "model_version": cfg["model_version"], "scenario": scen_name, "disclaimer": cfg["disclaimer"],
            "stage": "A: passenger growth opportunity (not terminal suitability, not project economics)",
            "constraints_as_of": as_of, "constraints_not_in_effect": ended, "capacity_rates_not_used": imc_rejected,
            "gate": {"min_enplanements": gate, "below_scale": below,
                     "no_faa_enplanement_record": no_record[:50], "n_no_record": len(no_record)}, "table": table, "not_scored": not_scored,
            "findings": findings, "max_rank_shift_across_scenarios":
                {r["airport"]: max(r["scenario_ranks"].values()) - min(r["scenario_ranks"].values()) for r in table}}
