"""Terminal-expansion opportunity screen (config/screening.toml).

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


def _verified_imc_rates(ctx) -> dict[str, float]:
    rows = ctx.engine.con.execute("""SELECT airport_iata, value FROM curated_constraint
        WHERE category = 'capacity_rate' AND verification LIKE 'verified:%' AND item ILIKE '%instrument%'""").fetchall()
    out: dict[str, float] = {}
    for code, val in rows:
        nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(val))]
        if nums:
            out[code] = max(out.get(code, 0.0), max(nums))   # best IMC configuration (conservative)
    return out


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
    # flags
    imc = _verified_imc_rates(ctx)
    ot_months = ctx.engine.available("ontime_dep")[-12:]
    caps = dict(ctx.engine.con.execute("""SELECT airport_iata, string_agg(item || ': ' || value, '; ')
        FROM curated_constraint WHERE category IN ('regulatory_cap', 'curfew') AND verification LIKE 'verified:%'
        GROUP BY 1""").fetchall())
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
        f = _new(ctx, metric_id=f"screen_score:{cfg['model_version']}", label=f"Expansion screen score — {code} ({scen_name})",
                 value=sc, unit="points (0-100, anchored scales)", fmt="number", epistemic_class="calculated",
                 definition="Σ weight × anchored score of: " + "; ".join(
                     f"{c['label']} [{c['lo']}→{c['hi']}, {c['scale']}] w={wi}" for c, wi in zip(comps, w)),
                 formula_version=cfg["model_version"], subject={"airport": aid, "airport_code": code, "rank": rank},
                 window={"label": "see inputs"}, sources=[s for x in fs for s in x.sources],
                 caveats=[cfg["disclaimer"], "TAF component is an FAA forecast (unconstrained)."], inputs=[x.id for x in fs])
        flags = []
        if code in caps:
            flags.append({"flag": "REGULATORY_CAP", "detail": caps[code], "class": "observed (verified curated)"})
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
            flags.append({"flag": "AIRFIELD_BINDING" if share and share > 0 else "AIRFIELD_HEADROOM_IMC",
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
                      "components": {c["id"]: {"input": {"id": x.id, "value": _round(x.value)}, "points": round(p, 1)}
                                     for c, x, p in zip(comps, fs, contrib)},
                      "scenario_ranks": {n: ranks_by_scen[n][aid] for n in weights},
                      "flags": flags,
                      "capital_context": {"npias_need_usd": n_ and {"id": n_.id, "value": _round(n_.value)},
                                          "grants_awarded_fy21_25_usd": gr and {"id": gr.id, "value": _round(gr.value)}}})
        findings.append(f.brief())
    return {"op": "screen", "model_version": cfg["model_version"], "scenario": scen_name, "disclaimer": cfg["disclaimer"],
            "gate": {"min_enplanements": gate, "below_scale": below}, "table": table, "not_scored": not_scored,
            "findings": findings, "max_rank_shift_across_scenarios":
                {r["airport"]: max(r["scenario_ranks"].values()) - min(r["scenario_ranks"].values()) for r in table}}
