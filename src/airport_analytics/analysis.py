"""Analysis specs -> deterministic operators -> Findings.

A spec is a small JSON object (see docs/05-analytics-architecture.md §4). Operators never invent
values: every number they emit is either a metric evaluated by the engine or a deterministic function
of such findings, and is registered in the EvidenceStore with its inputs.
"""
from __future__ import annotations

import math
import random
import tomllib
from dataclasses import dataclass
from typing import Any

from airport_data.config import REPO_ROOT

from .engine import Engine, MetricRef
from .evidence import EvidenceStore, Finding, InsufficientData, InvalidSpec, NotApplicable
from .resolver import Resolver
from .semantic import CATALOG_VERSION, CAVEATS, METRICS

OPS = ("aggregate", "rank", "correlate", "trend", "anomaly", "distribution", "forecast_vs_actual", "screen")
TRANSFORMS = ("pct_change", "abs_change", "cagr")
MAX_FINDINGS = 400


@dataclass
class Context:
    engine: Engine
    resolver: Resolver
    store: EvidenceStore


# ------------------------------------------------------------------ finding helpers
def _label(name: str, keys: dict[str, Any], window: str, ctx: Context, ids: list[int] | None = None) -> str:
    parts = [] if keys or not ids or len(ids) != 1 else [ctx.resolver.code(ids[0])]
    for k, v in keys.items():
        parts.append(ctx.resolver.code(v) if k == "airport" else f"{k}={v}")
    return f"{name} — {', '.join(parts) or 'group total'} — {window}"


def _subject(keys: dict[str, Any], ctx: Context, group_note: dict | None) -> dict[str, Any]:
    s = dict(keys)
    if "airport" in keys:
        s["airport_code"] = ctx.resolver.code(keys["airport"])
    elif group_note:
        s["entity_set"] = group_note.get("group") or [a["code"] for a in group_note.get("airports", [])]
    return s


def _caveat_texts(codes) -> list[str]:
    return [CAVEATS.get(c, c) for c in codes]


def _new(ctx: Context, **kw) -> Finding:
    if len(ctx.store.all()) > 50_000:
        raise InvalidSpec("session evidence store full")
    f = Finding(id=ctx.store.new_id(), catalog_version=CATALOG_VERSION, **kw)
    return ctx.store.add(f)


def _name(ref: MetricRef) -> str:
    return ref.metric.name + (f" ({', '.join(f'{k}={v}' for k, v in ref.params.items())})" if ref.params else "")


def _fmt_def(ref: MetricRef) -> str:
    try:
        return ref.metric.definition.format(**ref.params)
    except (KeyError, IndexError):
        return ref.metric.definition


# ------------------------------------------------------------------ metric evaluation with transforms
def _eval_refs(ctx: Context, spec: dict, ids: list[int], group_by: list[str], notes: dict) -> list[dict]:
    """Evaluate metric refs (with optional transform) -> list of {ref_key, keys, finding}."""
    out = []
    for raw in spec["metrics"]:
        tr = raw.get("transform") if isinstance(raw, dict) else None
        base_raw = {k: v for k, v in raw.items() if k not in ("transform", "window")} if isinstance(raw, dict) else raw
        ref = MetricRef.parse(base_raw)
        window = (raw.get("window") if isinstance(raw, dict) else None) or spec.get("window")
        res = ctx.engine.evaluate([ref], ids, window, group_by, spec.get("filters"))
        win_lab = "; ".join(sorted({w.label for w in res.windows.values()}))
        base = {}
        for row in res.rows:
            k = tuple(row["keys"].items())
            cav = list(ref.metric.caveats)
            cov = row.get("ontime_coverage")
            if cov and cov["ratio"] is not None and cov["ratio"] < 0.7:
                cav.append("ONTIME_LOW_COVERAGE")
            f = _new(ctx, metric_id=ref.key, label=_label(_name(ref), row["keys"], win_lab, ctx, ids),
                     value=row["values"][ref.key], unit=ref.metric.unit, fmt=ref.metric.fmt,
                     epistemic_class=res.classes[ref.key], definition=_fmt_def(ref),
                     formula_version=ref.metric.formula_version, subject=_subject(row["keys"], ctx, notes),
                     window={"label": win_lab, "spec": window or {"t12": True}}, sources=res.lineage[ref.key],
                     caveats=_caveat_texts(cav) + ([CAVEATS["TAF_FORECAST"]] if res.classes[ref.key] == "forecast"
                                                   and "TAF_FORECAST" not in cav else []),
                     coverage=cov, spec={"metrics": [base_raw], "entities": spec["entities"], "window": window,
                                         "group_by": group_by, "filters": spec.get("filters")})
            base[k] = f
        for n in res.notes:
            notes.setdefault("engine_notes", []).append(n) if n not in notes.get("engine_notes", []) else None
        if not tr:
            out += [{"ref": ref.key, "keys": dict(k), "finding": f} for k, f in base.items()]
            continue
        typ = tr.get("type")
        if typ not in TRANSFORMS:
            raise InvalidSpec(f"unknown transform {typ!r}", allowed=list(TRANSFORMS))
        cw = tr.get("compare_window")
        if not cw:
            if (window or {"t12": True}).get("t12"):
                cw = {"t12": True, "offset_months": int((window or {}).get("offset_months", 0)) + 12}
            else:
                raise InvalidSpec("transform needs compare_window")
        cres = ctx.engine.evaluate([ref], ids, cw, group_by, spec.get("filters"), attach_coverage=False)
        clab = "; ".join(sorted({w.label for w in cres.windows.values()}))
        years = None
        if typ == "cagr":
            years = tr.get("years")
            if not years:
                raise InvalidSpec("cagr transform needs 'years' (length of the interval)")
        for row in cres.rows:
            k = tuple(row["keys"].items())
            if k not in base:
                continue
            fb = base[k]
            fc = _new(ctx, metric_id=ref.key, label=_label(_name(ref), row["keys"], clab, ctx, ids),
                      value=row["values"][ref.key], unit=ref.metric.unit, fmt=ref.metric.fmt,
                      epistemic_class=cres.classes[ref.key], definition=_fmt_def(ref),
                      formula_version=ref.metric.formula_version, subject=fb.subject,
                      window={"label": clab, "spec": cw}, sources=cres.lineage[ref.key], caveats=fb.caveats,
                      spec={"metrics": [base_raw], "entities": spec["entities"], "window": cw, "group_by": group_by,
                            "filters": spec.get("filters")})
            a, b = fb.value, fc.value
            if a is None or b is None:
                v = None
            elif typ == "abs_change":
                v = a - b
            elif b == 0:
                v = None
            elif typ == "pct_change":
                v = a / b - 1
            else:
                v = (a / b) ** (1 / float(years)) - 1 if a > 0 and b > 0 else None
            cls = "forecast" if "forecast" in (fb.epistemic_class, fc.epistemic_class) else "calculated"
            name = {"pct_change": "change (%)", "abs_change": "change", "cagr": "CAGR"}[typ]
            ft = _new(ctx, metric_id=f"{typ}:{ref.key}", label=_label(f"{_name(ref)} {name}", row["keys"],
                                                                       f"{win_lab} vs {clab}", ctx, ids),
                      value=v, unit="ratio" if typ != "abs_change" else ref.metric.unit,
                      fmt="pct" if typ != "abs_change" else ref.metric.fmt, epistemic_class=cls,
                      definition=f"{name} of [{_fmt_def(ref)}]: {win_lab} vs {clab}", formula_version="1",
                      subject=fb.subject, window={"label": f"{win_lab} vs {clab}"}, sources=fb.sources + fc.sources,
                      caveats=fb.caveats, inputs=[fb.id, fc.id], coverage=fb.coverage)
            out.append({"ref": f"{typ}:{ref.key}", "keys": dict(k), "finding": ft})
    return out


def _table(items: list[dict]) -> list[dict]:
    rows: dict[tuple, dict] = {}
    for it in items:
        k = tuple(it["keys"].items())
        r = rows.setdefault(k, {**{kk: (vv if kk != "airport" else None) for kk, vv in it["keys"].items()}})
        if "airport" in it["keys"]:
            r["airport"] = it["finding"].subject.get("airport_code")
        r[it["ref"]] = {"id": it["finding"].id, "value": _round(it["finding"].value)}
    return list(rows.values())


def _round(v):
    if isinstance(v, float):
        return float(f"{v:.6g}")
    return v


# ------------------------------------------------------------------ statistics (pure, deterministic)
def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def _median(v: list[float]) -> float:
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _quantile(v: list[float], q: float) -> float:
    s = sorted(v)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ------------------------------------------------------------------ operators
def run_analysis(spec: dict[str, Any], ctx: Context) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise InvalidSpec("spec must be an object")
    op = spec.get("op", "aggregate")
    if op not in OPS:
        raise InvalidSpec(f"unknown op {op!r}", allowed=list(OPS))
    if op in ("aggregate", "rank", "trend", "anomaly", "distribution") and not spec.get("metrics") \
            and not (op == "rank" and (spec.get("options") or {}).get("criteria")):
        raise InvalidSpec(f"spec.metrics is required for op {op}")
    ids, notes = ctx.resolver.entities(spec.get("entities") or {})
    fn = {"aggregate": _op_aggregate, "rank": _op_rank, "correlate": _op_correlate, "trend": _op_trend,
          "anomaly": _op_anomaly, "distribution": _op_distribution, "forecast_vs_actual": _op_fva,
          "screen": _op_screen}[op]
    result = fn(spec, ids, notes, ctx)
    result["entities"] = notes
    if notes.get("engine_notes"):
        result["notes"] = notes.pop("engine_notes")
    n = len(result.get("findings", []))
    if n > MAX_FINDINGS:
        result["findings"] = result["findings"][:MAX_FINDINGS]
        result["truncated"] = f"{n} findings; first {MAX_FINDINGS} returned (narrow the spec)"
    return result


def _default_group(spec, ids):
    gb = spec.get("group_by")
    if gb is None:
        gb = ["airport"] if len(ids) > 1 else []
    return list(gb)


def _op_aggregate(spec, ids, notes, ctx):
    items = _eval_refs(ctx, spec, ids, _default_group(spec, ids), notes)
    return {"op": "aggregate", "table": _table(items), "findings": [i["finding"].brief() for i in items]}


def _per_airport(spec, ids, notes, ctx, refs_raw) -> dict[str, dict[int, Finding]]:
    s = dict(spec, metrics=refs_raw, group_by=["airport"])
    out: dict[str, dict[int, Finding]] = {}
    for it in _eval_refs(ctx, s, ids, ["airport"], notes):
        out.setdefault(it["ref"], {})[it["keys"]["airport"]] = it["finding"]
    return out


def _op_rank(spec, ids, notes, ctx):
    """Rank airports by one metric, or by a transparent weighted composite of dynamically chosen metrics."""
    opts = spec.get("options") or {}
    crit = opts.get("criteria") or [{"metric": (spec.get("metrics") or [None])[0], "weight": 1.0,
                                     "direction": opts.get("direction", "higher_better")}]
    scaling = opts.get("scaling", "minmax_in_set")
    if scaling not in ("minmax_in_set", "rank_in_set"):
        raise InvalidSpec("scaling must be minmax_in_set or rank_in_set")
    raw_refs = [c["metric"] for c in crit]
    vals = _per_airport(spec, ids, notes, ctx, raw_refs)
    keys = list(vals)
    if len(keys) != len(crit):   # transforms produce prefixed keys; map by order
        raise InvalidSpec("each criterion must reference a distinct metric")
    tot_w = sum(float(c.get("weight", 1)) for c in crit)
    scored, not_scored = [], []
    for aid in ids:
        fs = [vals[k].get(aid) for k in keys]
        if any(f is None or f.value is None for f in fs):
            not_scored.append({"airport": ctx.resolver.code(aid), "missing": [k for k, f in zip(keys, fs) if f is None or f.value is None]})
            continue
        scored.append((aid, fs))
    if len(scored) < 2:
        raise InsufficientData("fewer than 2 airports have all ranking inputs", not_scored=not_scored)
    contrib = {aid: [] for aid, _ in scored}
    for j, (k, c) in enumerate(zip(keys, crit)):
        xs = [fs[j].value for _, fs in scored]
        hb = c.get("direction", "higher_better") == "higher_better"
        if scaling == "minmax_in_set":
            lo, hi = min(xs), max(xs)
            s = [0.5 if hi == lo else ((x - lo) / (hi - lo) if hb else (hi - x) / (hi - lo)) for x in xs]
        else:
            rk = _ranks(xs if hb else [-x for x in xs])
            s = [(r - 1) / (len(xs) - 1) for r in rk]
        for (aid, _), sv in zip(scored, s):
            contrib[aid].append(100 * float(c.get("weight", 1)) / tot_w * sv)
    order = sorted(scored, key=lambda t: -sum(contrib[t[0]]))
    findings, table = [], []
    for rank, (aid, fs) in enumerate(order, 1):
        score = sum(contrib[aid])
        f = _new(ctx, metric_id="rank_score", label=f"Ranking score — {ctx.resolver.code(aid)}", value=score,
                 unit="points (0-100, relative to this set)", fmt="number", epistemic_class="calculated",
                 definition=f"Σ weight × {scaling}-scaled criterion; criteria: " +
                 ", ".join(f"{k} ({c.get('direction', 'higher_better')}, w={c.get('weight', 1)})" for k, c in zip(keys, crit)),
                 formula_version="1", subject={"airport": aid, "airport_code": ctx.resolver.code(aid), "rank": rank},
                 window={"label": "see inputs"}, sources=[s for x in fs for s in x.sources],
                 caveats=["Scores are relative to the airports in this set; adding/removing airports changes them."],
                 inputs=[x.id for x in fs])
        findings.append(f.brief())
        table.append({"rank": rank, "airport": ctx.resolver.code(aid), "score": {"id": f.id, "value": _round(score)},
                      **{k: {"id": x.id, "value": _round(x.value), "points": round(p, 2)} for k, x, p in zip(keys, fs, contrib[aid])}})
    return {"op": "rank", "table": table, "findings": findings, "not_scored": not_scored,
            "method": {"scaling": scaling, "criteria": crit}}


def _op_correlate(spec, ids, notes, ctx):
    opts = spec.get("options") or {}
    if not (opts.get("x") and opts.get("y")):
        raise InvalidSpec("correlate needs options.x and options.y (metric refs, transforms allowed)")
    vals = _per_airport(spec, ids, notes, ctx, [opts["x"], opts["y"]])
    (kx, X), (ky, Y) = list(vals.items())
    pts = [(a, X[a], Y[a]) for a in X if a in Y and X[a].value is not None and Y[a].value is not None]
    n = len(pts)
    if n < 8:
        raise InsufficientData(f"correlation needs ≥8 airports with both values; have {n}")
    xs, ys = [p[1].value for p in pts], [p[2].value for p in pts]
    pr, sr = _pearson(xs, ys), _pearson(_ranks(xs), _ranks(ys))
    rng = random.Random(0)
    boots = []
    for _ in range(1000):
        idx = [rng.randrange(n) for _ in range(n)]
        v = _pearson(_ranks([xs[i] for i in idx]), _ranks([ys[i] for i in idx]))
        if v is not None:
            boots.append(v)
    ci = (_quantile(boots, 0.025), _quantile(boots, 0.975)) if boots else (None, None)
    inputs = [p[1].id for p in pts] + [p[2].id for p in pts]
    srcs = pts[0][1].sources + pts[0][2].sources
    cav = ["Association across airports, not causation; confounders (size, hub status, region) are not controlled.",
           f"n = {n} airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ."]
    fs = []
    for mid, v, d in (("pearson_r", pr, "Pearson correlation"), ("spearman_rho", sr, "Spearman rank correlation"),
                      ("spearman_ci_low", ci[0], "Spearman ρ 95% bootstrap CI, lower"),
                      ("spearman_ci_high", ci[1], "Spearman ρ 95% bootstrap CI, upper"), ("n", n, "airports used")):
        f = _new(ctx, metric_id=mid, label=f"{d}: {kx} vs {ky}", value=v, unit="" if mid != "n" else "airports",
                 fmt="ratio" if mid != "n" else "number", epistemic_class="calculated",
                 definition=f"{d} of [{kx}] and [{ky}] across airports", formula_version="1",
                 subject={"entity_set": notes.get("group") or "listed airports"}, window={"label": "see inputs"},
                 sources=srcs, caveats=cav, inputs=inputs)
        fs.append(f.brief())
    table = [{"airport": ctx.resolver.code(a), kx: {"id": fx.id, "value": _round(fx.value)},
              ky: {"id": fy.id, "value": _round(fy.value)}} for a, fx, fy in pts]
    return {"op": "correlate", "findings": fs, "table": table}


def _op_trend(spec, ids, notes, ctx):
    gb = ["month"] + (["airport"] if len(ids) > 1 and "airport" in _default_group(spec, ids) else [])
    s = dict(spec, group_by=gb)
    items = _eval_refs(ctx, s, ids, gb, notes)
    series: dict[tuple, list] = {}
    for it in items:
        k = (it["ref"], it["keys"].get("airport"))
        series.setdefault(k, []).append(it)
    findings = [it["finding"].brief() for it in items]
    summary = []
    for (ref, aid), its in series.items():
        its.sort(key=lambda i: i["keys"]["month"])
        pts = [(i["keys"]["month"], i["finding"]) for i in its if i["finding"].value is not None]
        if len(pts) < 6:
            continue
        xs = list(range(len(pts)))
        ys = [p[1].value for p in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        yoy = None
        if len(pts) >= 13:
            last, prior = pts[-1][1].value, dict((m, f) for m, f in pts).get(_shift(pts[-1][0], -12))
            if prior is not None and prior.value:
                yoy = last / prior.value - 1
        who = ctx.resolver.code(aid) if aid else (ctx.resolver.code(ids[0]) if len(ids) == 1 else (notes.get("group") or "set"))
        fsl = _new(ctx, metric_id=f"trend_slope:{ref}", label=f"Linear trend per month — {ref} — {who}",
                   value=slope, unit=f"{pts[0][1].unit} per month", fmt="number", epistemic_class="calculated",
                   definition=f"OLS slope of monthly {ref}, {pts[0][0]}…{pts[-1][0]}", formula_version="1",
                   subject={"airport": aid, "airport_code": who}, window={"label": f"{pts[0][0]}…{pts[-1][0]}"},
                   sources=pts[0][1].sources, caveats=["Monthly series include seasonality; slope is descriptive."],
                   inputs=[p[1].id for p in pts])
        row = {"series": ref, "airport": who, "slope_per_month": {"id": fsl.id, "value": _round(slope)},
               "first": {"month": pts[0][0], "id": pts[0][1].id}, "last": {"month": pts[-1][0], "id": pts[-1][1].id}}
        findings.append(fsl.brief())
        if yoy is not None:
            fy = _new(ctx, metric_id=f"yoy:{ref}", label=f"YoY change of last month — {ref} — {who}", value=yoy,
                      unit="ratio", fmt="pct", epistemic_class="calculated",
                      definition=f"{pts[-1][0]} vs {_shift(pts[-1][0], -12)}", formula_version="1",
                      subject={"airport": aid, "airport_code": who}, window={"label": pts[-1][0]},
                      sources=pts[0][1].sources, inputs=[pts[-1][1].id])
            findings.append(fy.brief())
            row["last_month_yoy"] = {"id": fy.id, "value": _round(yoy)}
        summary.append(row)
    return {"op": "trend", "summary": summary, "table": _table(items)[:120], "findings": findings}


def _shift(ym: str, k: int) -> str:
    y, m = map(int, ym.split("-"))
    n = y * 12 + m - 1 + k
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def _op_anomaly(spec, ids, notes, ctx):
    """mode=cross_section: robust z of each airport vs the set; mode=time: robust z of monthly YoY changes."""
    opts = spec.get("options") or {}
    mode = opts.get("mode", "cross_section")
    thr = float(opts.get("z_threshold", 3.5))
    flagged, findings = [], []
    if mode == "cross_section":
        vals = _per_airport(spec, ids, notes, ctx, spec["metrics"][:1])
        (k, F), = vals.items()
        pts = [(a, f) for a, f in F.items() if f.value is not None]
        if len(pts) < 8:
            raise InsufficientData(f"need ≥8 airports with values, have {len(pts)}")
        v = [f.value for _, f in pts]
        med = _median(v)
        mad = _median([abs(x - med) for x in v]) * 1.4826
        if mad == 0:
            raise InsufficientData("dispersion (MAD) is zero; robust z undefined")
        for a, f in pts:
            z = (f.value - med) / mad
            if abs(z) >= thr:
                fz = _new(ctx, metric_id=f"robust_z:{k}", label=f"Robust z-score — {k} — {ctx.resolver.code(a)}", value=z,
                          unit="MADs", fmt="number", epistemic_class="calculated",
                          definition=f"(value − median of set) / (1.4826·MAD), set of {len(pts)} airports",
                          formula_version="1", subject={"airport": a, "airport_code": ctx.resolver.code(a)},
                          window=f.window, sources=f.sources, inputs=[f.id],
                          caveats=["Outlier relative to this set; not necessarily an error or a problem."])
                findings.append(fz.brief())
                flagged.append({"airport": ctx.resolver.code(a), "value": {"id": f.id, "value": _round(f.value)},
                                "robust_z": {"id": fz.id, "value": _round(z)}})
        return {"op": "anomaly", "mode": mode, "flagged": flagged, "findings": findings,
                "set_median": _round(med), "n": len(pts)}
    if mode != "time":
        raise InvalidSpec("anomaly mode must be cross_section or time")
    s = dict(spec, group_by=["month", "airport"], window=spec.get("window") or {"start": "2024-01"})
    items = _eval_refs(ctx, s, ids, ["month", "airport"], notes)
    by: dict[int, dict[str, Finding]] = {}
    for it in items:
        by.setdefault(it["keys"]["airport"], {})[it["keys"]["month"]] = it["finding"]
    for a, ser in by.items():
        yoy = []
        for m, f in sorted(ser.items()):
            p = ser.get(_shift(m, -12))
            if p and p.value and f.value is not None:
                yoy.append((m, f.value / p.value - 1, f, p))
        if len(yoy) < 6:
            continue
        v = [y for _, y, _, _ in yoy]
        med = _median(v)
        mad = _median([abs(x - med) for x in v]) * 1.4826
        if mad == 0:
            continue
        for m, y, f, p in yoy:
            z = (y - med) / mad
            if abs(z) >= thr:
                fz = _new(ctx, metric_id="yoy_robust_z", label=f"Unusual YoY change — {ctx.resolver.code(a)} {m}",
                          value=y, unit="ratio", fmt="pct", epistemic_class="calculated",
                          definition=f"YoY change {m} vs {_shift(m, -12)}; robust z = {z:.1f} vs the airport's own YoY history",
                          formula_version="1", subject={"airport": a, "airport_code": ctx.resolver.code(a), "month": m},
                          window={"label": m}, sources=f.sources, inputs=[f.id, p.id],
                          caveats=["Flags unusual changes; causes (strikes, weather, schedule changes, data revisions) are not identified."])
                findings.append(fz.brief())
                flagged.append({"airport": ctx.resolver.code(a), "month": m, "yoy": {"id": fz.id, "value": _round(y)},
                                "robust_z": round(z, 2)})
    return {"op": "anomaly", "mode": mode, "flagged": flagged, "findings": findings}


def _op_distribution(spec, ids, notes, ctx):
    vals = _per_airport(spec, ids, notes, ctx, spec["metrics"][:1])
    (k, F), = vals.items()
    v = [f.value for f in F.values() if f.value is not None]
    if len(v) < 5:
        raise InsufficientData(f"need ≥5 airports with values, have {len(v)}")
    findings = []
    srcs = next(iter(F.values())).sources
    for q in (0.1, 0.25, 0.5, 0.75, 0.9):
        f = _new(ctx, metric_id=f"quantile:{k}", label=f"P{int(q * 100)} of {k} across set", value=_quantile(v, q),
                 unit=next(iter(F.values())).unit, fmt=next(iter(F.values())).fmt, epistemic_class="calculated",
                 definition=f"{int(q * 100)}th percentile (linear interpolation) across {len(v)} airports",
                 formula_version="1", subject={"entity_set": notes.get("group") or "listed airports"},
                 window=next(iter(F.values())).window, sources=srcs, inputs=[x.id for x in F.values()])
        findings.append(f.brief())
    return {"op": "distribution", "n": len(v), "findings": findings}


def _op_fva(spec, ids, notes, ctx):
    """FAA TAF forecast for a fiscal year vs the actual outcome from observed sources."""
    opts = spec.get("options") or {}
    fy = int(opts.get("fy", ctx.engine.taf_last_historical + 1))
    quantity = opts.get("quantity", "enplanements")
    if fy <= ctx.engine.taf_last_historical:
        raise NotApplicable(f"FY{fy} is historical in the TAF release (last historical FY{ctx.engine.taf_last_historical}); "
                            "no forecast to evaluate")
    pairs = {"enplanements": ("taf_enplanements", "passengers"), "operations": ("taf_operations", "tower_operations")}
    if quantity not in pairs:
        raise InvalidSpec("quantity must be enplanements or operations")
    fm, am = pairs[quantity]
    s = dict(spec, metrics=[{"id": fm, "window": {"fy": fy}}, {"id": am, "window": {"fy": fy}}])
    vals = _per_airport(s, ids, notes, ctx, s["metrics"])
    F, A = vals[fm], vals[am]
    table, findings = [], []
    for aid in ids:
        f, a = F.get(aid), A.get(aid)
        if not f or not a or f.value in (None, 0) or a.value is None:
            continue
        err = a.value / f.value - 1
        fe = _new(ctx, metric_id=f"forecast_error:{quantity}", label=f"Actual vs TAF forecast — {ctx.resolver.code(aid)} FY{fy}",
                  value=err, unit="ratio", fmt="pct", epistemic_class="calculated",
                  definition=f"actual {am} FY{fy} / TAF {fm} FY{fy} − 1", formula_version="1",
                  subject={"airport": aid, "airport_code": ctx.resolver.code(aid)}, window={"label": f"FY{fy}"},
                  sources=f.sources + a.sources, inputs=[f.id, a.id],
                  caveats=["Actual from T-100 segment enplanements (FAA TAF uses ACAIS-style enplanements; definitions differ by ~1%)."
                           if quantity == "enplanements" else "Actual from ATADS tower counts (TAF history is built from them)."])
        findings += [f.brief(), a.brief(), fe.brief()]
        table.append({"airport": ctx.resolver.code(aid), "forecast": {"id": f.id, "value": _round(f.value)},
                      "actual": {"id": a.id, "value": _round(a.value)}, "error": {"id": fe.id, "value": _round(err)}})
    if not table:
        raise InsufficientData("no airport has both forecast and actual for this fiscal year")
    return {"op": "forecast_vs_actual", "fy": fy, "quantity": quantity, "table": table, "findings": findings}


# ------------------------------------------------------------------ screening model
def load_screening(path=None) -> dict:
    return tomllib.loads((path or REPO_ROOT / "config" / "screening.toml").read_text())


def _op_screen(spec, ids, notes, ctx):
    from .screening import screen
    return screen(spec, ids, notes, ctx)
