"""Local evidence: the data behind a finding, recomputed with the engine's own definitions (read-only).

For a catalog-metric finding the semantic layer knows exactly which fact table, filters and aggregates produced it
(metric -> measures -> fact relation). So, for the finding's airport(s), period window and breakdown keys, we show:

  * calculation: every measure (numerator, denominator, ...) per period and in total, the metric expression, and the
    value recomputed from those totals (checked against the stored finding);
  * records: the contributing rows of the fact table, paginated, with the measure columns, a "counted" flag per
    measure filter, and the source file version (_period/_vintage_id) each row was loaded from.

Traceability levels, stated honestly in the result:
  records    - catalog metric over an airport-level fact: exact rows and aggregates
  aggregates - non-additive or custom metric: rows of the underlying table, without a per-measure breakdown
  inputs     - derived findings (change, ratio, screen score, forecast error): the input findings and the formula
  source     - only the source files and periods are known (static, area-level or exploratory results)
Nothing here changes a formula: the SQL is assembled from the same FACTS / MEASURES definitions the engine uses.
"""
from __future__ import annotations

import re
from typing import Any

from .engine import Engine, MetricRef
from .evidence import Finding
from .semantic import FACTS, METRICS, eval_expr, metric_expr, metric_measures

PAGE = 25
ID_COLS = ("period_month", "fiscal_year", "flight_date", "year", "month", "locid", "carrier", "unique_carrier_name",
           "reporting_airline", "origin", "dest", "service_type", "aircraft_config_desc", "class_desc", "scenario",
           "record_type", "grant_number", "project_summary")
LINEAGE = ("_period", "_vintage_id")
_MID = re.compile(r"^([a-z0-9_]+)\((.*)\)$")


def _params(metric_id: str) -> tuple[str, dict[str, Any]]:
    m = _MID.match(metric_id or "")
    if not m:
        return metric_id, {}
    out = {}
    for kv in m.group(2).split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k] = int(v) if re.fullmatch(r"-?\d+", v) else float(v) if re.fullmatch(r"-?\d+\.\d+", v) else v
    return m.group(1), out


def _filter_of(agg: str) -> str | None:
    m = re.search(r"FILTER\s*\(\s*WHERE\s+(.*)\)\s*$", agg, re.I | re.S)
    return m.group(1).strip() if m else None


def _tlist(engine: Engine, kind: str, periods: list) -> str:
    return engine.month_list(periods) if kind == "month" else ", ".join(str(int(p)) for p in periods) or "NULL"


def _plain(v: Any) -> Any:
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    if isinstance(v, float):
        return round(v, 6)
    return v


def _scope(engine: Engine, f: Finding, fact_id: str):
    """(airport_ids, extra WHERE clauses, resolved window) for the finding, from what it recorded."""
    fact = FACTS[fact_id]
    subj = f.subject or {}
    ids = [int(subj["airport"])] if subj.get("airport") is not None else \
        [int(i) for i in ((f.execution or {}).get("resolved_airport_ids") or [])][:400]
    where, notes = [], []
    for k, v in subj.items():
        if k in fact.dims and k not in ("airport",):
            where.append(f"({fact.dims[k]}) = {_lit(v)}")
            notes.append(f"{k} = {v}")
    win_spec = (f.window or {}).get("spec")
    win = engine.resolve_window(win_spec, fact_id)
    periods = list(win.periods)
    if "month" in subj and fact.time_kind == "month":
        periods = [str(subj["month"])[:7]]
    for k in ("year", "fiscal_year"):
        if k in subj and fact.time_kind in ("cy", "fy"):
            periods = [int(subj[k])]
    return ids, where, win, periods, notes


def _lit(v: Any) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def data_used(engine: Engine, f: Finding, store=None, page: int = 0) -> dict[str, Any]:
    page = max(0, int(page))
    base, params = _params(f.metric_id)
    if f.inputs and base not in METRICS:
        return {"level": "inputs", "summary": "Derived from other findings; open each input to see its data.",
                "formula": f.definition,
                "inputs": [{"id": i, "label": store.get(i).label if store and i in store else i,
                            "value": store.get(i).value if store and i in store else None} for i in f.inputs]}
    if base == "exploratory_sql":
        return {"level": "source", "summary": "Exploratory SQL result (not a catalog metric); the query is shown.",
                "query": (f.spec or {}).get("sql")}
    m = METRICS.get(base)
    if not m:
        return {"level": "source", "summary": "Only the source files and periods are recorded for this result."}
    ref = MetricRef.parse({"id": base, "params": params})
    measures = metric_measures(m, ref.params)
    fact_id = next(iter({ms.fact for ms, _ in measures.values()}), None) or m.custom_fact
    if not fact_id or fact_id not in FACTS:
        return {"level": "source", "summary": "This metric has no single fact table to show rows from."}
    fact = FACTS[fact_id]
    if fact.area_key or fact.time_kind == "static":
        return {"level": "source", "summary": "Area-level or static reference value: the source files and periods are "
                                              "shown; it is not a sum of airport-level records."}
    ids, extra, win, periods, notes = _scope(engine, f, fact_id)
    if not ids:
        return {"level": "source", "summary": "The airport set for this result was not recorded."}
    tcond = f"t IN ({_tlist(engine, fact.time_kind, periods)})" if periods else "TRUE"
    where = " AND ".join([f"airport_id IN ({engine.id_list(ids)})", tcond, *extra])
    rel = f"({fact.relation}) r"
    con = engine.con
    out: dict[str, Any] = {"fact": fact_id, "fact_description": fact.description, "airports": len(ids),
                           "window": win.label, "periods": [str(p) for p in periods], "filters": notes,
                           "level": "records" if measures else "aggregates"}
    # ---- calculation: each measure per period and in total, then the metric recomputed from the totals
    if measures:
        names = list(measures)
        sel = ", ".join(f"{ms.agg.format(**bp)} AS \"{n}\"" for n, (ms, bp) in measures.items())
        per = con.execute(f"SELECT t, {sel} FROM {rel} WHERE {where} GROUP BY t ORDER BY t").fetchall()
        tot = con.execute(f"SELECT {sel} FROM {rel} WHERE {where}").fetchone()
        totals = dict(zip(names, [float(x) if x is not None else None for x in tot]))
        expr = metric_expr(m)
        recomputed = eval_expr(expr, totals)
        same = isinstance(recomputed, (int, float)) and isinstance(f.value, (int, float)) and \
            abs(recomputed - f.value) <= 1e-9 * max(1.0, abs(f.value))
        out["calculation"] = {
            "expression": expr, "measures": [{"name": n, "sql": ms.agg.format(**bp),
                                              "counts_only": _filter_of(ms.agg.format(**bp))} for n, (ms, bp) in measures.items()],
            "by_period": [{"period": _plain(r[0]), **{n: _plain(v) for n, v in zip(names, r[1:])}} for r in per],
            "totals": totals, "recomputed": recomputed, "matches_finding": same}
    # ---- records: the contributing rows (bounded page), with lineage and "counted" flags
    cols = [d[0] for d in con.execute(f"SELECT * FROM {rel} LIMIT 0").description]
    used = []
    for ms, bp in measures.values():
        used += [c for c in re.findall(r"[a-z_][a-z0-9_]*", ms.agg.format(**bp).lower()) if c in cols]
    show = list(dict.fromkeys([c for c in ID_COLS if c in cols][:7] + used + [c for c in LINEAGE if c in cols]))[:16]
    flags = {}
    for n, (ms, bp) in measures.items():
        flt = _filter_of(ms.agg.format(**bp))
        if flt and flt not in flags.values():
            flags[f"counted_in_{n}"] = flt
    flag_sel = "".join(f", ({e}) AS \"{k}\"" for k, e in list(flags.items())[:3])
    n_rows = con.execute(f"SELECT count(*) FROM {rel} WHERE {where}").fetchone()[0]
    order = ", ".join(c for c in ("t", "carrier", "origin", "dest", "flight_date") if c in cols or c == "t")
    rows = con.execute(f"SELECT {', '.join(show)}{flag_sel} FROM {rel} WHERE {where} ORDER BY {order} "
                       f"LIMIT {PAGE} OFFSET {page * PAGE}").fetchall()
    out["records"] = {"columns": show + list(flags)[:3], "rows": [[_plain(v) for v in r] for r in rows],
                      "total": n_rows, "page": page, "page_size": PAGE,
                      "counted_flags": {k: v for k, v in list(flags.items())[:3]},
                      "note": "Rows as loaded into the database from the original file (conformed columns). "
                              "_period and _vintage_id identify the exact downloaded file each row came from."}
    out["summary"] = (f"{n_rows:,} records of {fact.description or fact_id} for "
                      f"{'this airport' if len(ids) == 1 else f'{len(ids)} airports'}, {win.label}"
                      + (f", {', '.join(notes)}" if notes else "") + ".")
    if not measures:
        out["summary"] += (" This metric uses a custom calculation (see the definition), which may apply further filters "
                           "or ordering; the rows shown are those of the underlying table for the same airport and "
                           "window, not an exact list of contributing rows.")
    return out
