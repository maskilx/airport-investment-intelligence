"""Charts from evidence: a closed ChartSpec in, a Vega-Lite spec + inspectable rows out.

The model chooses only *which findings* to plot, the chart type and a (number-free, validated) title. Every plotted value is
read from the evidence store, so a chart can never show a number that is not a finding. Each mark carries its finding id,
so the UI can open the provenance of any bar or point.
"""
from __future__ import annotations

from typing import Any

from airport_analytics.evidence import EvidenceStore, Finding
from airport_analytics.render import fmt_value

TYPES = ("auto", "bar", "line", "scatter", "table")
TIME_KEYS = ("month", "year", "fiscal_year", "cy", "fy", "hour")
SKIP_KEYS = {"entity_set", "airport_id", "group", "derived_from", "airport_name", "scenario"}
AXIS_FMT = {"pct": ".0%", "usd": "$,.3s", "minutes": ".1f", "ratio": ".2f"}


def _metric_name(f: Finding) -> str:
    return f.label.split(" — ")[0]


def _dims(f: Finding) -> tuple[str | None, Any, str | None, Any]:
    """-> (time_key, time_value, category_key, category_value)."""
    tk = next((k for k in TIME_KEYS if k in f.subject), None)
    ck = "airport_code" if f.subject.get("airport_code") else next(
        (k for k in f.subject if k not in SKIP_KEYS and k not in TIME_KEYS and k != "airport_code"), None)
    return tk, f.subject.get(tk) if tk else None, ck, f.subject.get(ck) if ck else None


def _row(f: Finding) -> dict:
    tk, tv, ck, cv = _dims(f)
    return {"fid": f.id, "value": f.value, "formatted": fmt_value(f), "metric": _metric_name(f), "unit": f.unit,
            "fmt": f.fmt, "class": f.epistemic_class, "period": f.window.get("label", ""), "label": f.label,
            "time": str(tv) if tv is not None else None, "time_key": tk,
            "category": str(cv) if cv is not None else None, "category_key": ck}


def build_chart(spec: dict, store: EvidenceStore, idx: int = 0) -> dict:
    ctype = spec.get("type", "auto")
    if ctype not in TYPES:
        ctype = "auto"
    fs = [store.get(i) for i in dict.fromkeys(spec.get("findings") or []) if i in store]
    rows = [_row(f) for f in fs]
    notes = []
    num = [r for r in rows if isinstance(r["value"], (int, float))]
    dropped = [r["fid"] for r in rows if r not in num]
    if dropped:
        notes.append(f"not plotted (no numeric value / not established): {', '.join(dropped)}")
    title = (spec.get("title") or "").strip() or (num[0]["metric"] if num else "Findings")
    out = {"id": f"chart{idx + 1}", "title": title, "rows": rows, "findings": [r["fid"] for r in rows], "notes": notes}
    metrics = list(dict.fromkeys(r["metric"] for r in num))
    units = list(dict.fromkeys(r["unit"] for r in num))
    if ctype == "auto":
        ctype = "scatter" if len(metrics) == 2 and spec.get("type") == "scatter" else (
            "line" if num and all(r["time"] for r in num) and len({r["time"] for r in num}) >= 3 else "bar")
    if ctype != "table" and len(num) < 1:
        ctype = "table"
    if ctype in ("bar", "line") and len(units) > 1:
        notes.append(f"mixed units {units}: shown as a table instead of one axis")
        ctype = "table"
    out["type"] = ctype
    if ctype == "table":
        out["vega_lite"] = None
        return out
    fmt = AXIS_FMT.get(num[0]["fmt"], ",.3~s")
    tooltip = [{"field": "label", "title": "Finding"}, {"field": "formatted", "title": "Value"},
               {"field": "class", "title": "Class"}, {"field": "period", "title": "Period"}, {"field": "fid", "title": "Id"}]
    base = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "data": {"values": num},
            "width": "container", "height": 260, "usermeta": {"finding_field": "fid"}}
    if ctype == "scatter":
        if len(metrics) != 2:
            notes.append("scatter needs exactly two metrics; shown as bars")
            ctype = out["type"] = "bar"
        else:
            by = {}
            for r in num:
                by.setdefault(r["category"], {})[r["metric"]] = r
            pts = [{"category": c, "x": d[metrics[0]]["value"], "y": d[metrics[1]]["value"],
                    "fid": f"{d[metrics[0]]['fid']},{d[metrics[1]]['fid']}",
                    "x_fmt": d[metrics[0]]["formatted"], "y_fmt": d[metrics[1]]["formatted"]}
                   for c, d in by.items() if len(d) == 2]
            out["vega_lite"] = {**base, "data": {"values": pts}, "layer": [
                {"mark": {"type": "point", "filled": True, "size": 70}},
                {"mark": {"type": "text", "dy": -9, "fontSize": 10}, "encoding": {"text": {"field": "category"}}}],
                "encoding": {"x": {"field": "x", "type": "quantitative", "title": metrics[0]},
                             "y": {"field": "y", "type": "quantitative", "title": metrics[1]},
                             "tooltip": [{"field": "category"}, {"field": "x_fmt", "title": metrics[0]},
                                         {"field": "y_fmt", "title": metrics[1]}, {"field": "fid", "title": "Ids"}]}}
            return out
    series_field = "metric" if len(metrics) > 1 else ("category" if any(r["time"] for r in num) and
                                                      len({r["category"] for r in num}) > 1 else None)
    if ctype == "line":
        enc = {"x": {"field": "time", "type": "ordinal", "title": num[0]["time_key"] or "period", "sort": "ascending"},
               "y": {"field": "value", "type": "quantitative", "title": num[0]["unit"], "axis": {"format": fmt}},
               "tooltip": tooltip}
        if series_field:
            enc["color"] = {"field": series_field, "type": "nominal", "title": None}
        out["vega_lite"] = {**base, "mark": {"type": "line", "point": True}, "encoding": enc}
        return out
    xfield = "category" if any(r["category"] for r in num) else ("time" if any(r["time"] for r in num) else "label")
    enc = {"x": {"field": xfield, "type": "nominal", "title": None, "sort": None if xfield == "time" else "-y",
                 "axis": {"labelAngle": 0 if len(num) <= 8 else -40}},
           "y": {"field": "value", "type": "quantitative", "title": num[0]["unit"], "axis": {"format": fmt}},
           "opacity": {"condition": {"test": "datum['class'] == 'forecast' || datum['class'] == 'estimated'", "value": 0.55},
                       "value": 1},
           "tooltip": tooltip}
    if series_field and series_field != xfield:
        enc["color"] = {"field": series_field, "type": "nominal", "title": None}
        enc["xOffset"] = {"field": series_field}
    out["vega_lite"] = {**base, "mark": {"type": "bar", "cornerRadiusEnd": 2}, "encoding": enc}
    return out


def auto_chart_spec(cited: list[str], store: EvidenceStore) -> dict | None:
    """When the answer requested no chart: chart the largest group of ≥3 numeric cited findings sharing metric and unit."""
    groups: dict[tuple, list[str]] = {}
    for fid in cited:
        if fid not in store:
            continue
        f = store.get(fid)
        if isinstance(f.value, (int, float)) and not f.metric_id.startswith("derived:"):
            groups.setdefault((f.metric_id, f.unit), []).append(fid)
    best = max(groups.values(), key=len, default=[])
    return {"type": "auto", "title": "", "findings": best} if len(best) >= 3 else None


def build_charts(structured: dict, store: EvidenceStore) -> list[dict]:
    specs = structured.get("charts") or []
    if not specs:
        a = auto_chart_spec(structured.get("evidence") or [], store)
        specs = [a] if a else []
    return [build_chart(s, store, i) for i, s in enumerate(specs[:4])]
