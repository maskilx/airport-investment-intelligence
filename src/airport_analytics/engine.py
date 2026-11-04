"""Metric evaluation engine: windows, coverage, SQL compilation over the semantic layer, lineage.

One public entry point: `Engine.evaluate(...)`. Everything is deterministic; the only inputs are the
built database and the request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import duckdb

from airport_data.db import connect

from .evidence import InsufficientData, InvalidSpec, NotApplicable, OutOfCoverage, SourceRef
from .semantic import (AIRPORT_ATTR_DIMS, FACTS, METRICS, Measure, Metric, Param, eval_expr, metric_expr,
                       metric_measures)

STOCK_FACTS = {"area_cbsa", "area_county", "npias", "airport_attr"}   # never summed over time
TIME_DIMS = ("month", "year", "fiscal_year")


def _ym(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _add_months(ym: str, k: int) -> str:
    y, m = map(int, ym.split("-"))
    n = y * 12 + (m - 1) + k
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def _months_between(a: str, b: str) -> list[str]:
    out, cur = [], a
    while cur <= b:
        out.append(cur)
        cur = _add_months(cur, 1)
    return out


@dataclass
class MetricRef:
    metric: Metric
    params: dict[str, Any]
    key: str                         # e.g. "long_haul_share(min_miles=3000,scope=passenger,weight=passengers)"

    @staticmethod
    def parse(ref: Any) -> "MetricRef":
        if isinstance(ref, str):
            mid, raw = ref, {}
        elif isinstance(ref, dict) and "id" in ref:
            mid, raw = ref["id"], dict(ref.get("params") or {})
        else:
            raise InvalidSpec(f"metric reference must be an id or {{id, params}}: {ref!r}")
        if mid not in METRICS:
            raise InvalidSpec(f"unknown metric '{mid}'", known=sorted(METRICS))
        m = METRICS[mid]
        params: dict[str, Any] = {}
        for p in m.params:
            v = raw.pop(p.name, p.default)
            params[p.name] = _check_param(p, v)
        if raw:
            raise InvalidSpec(f"unknown parameter(s) for {mid}: {sorted(raw)}", allowed=[p.name for p in m.params])
        key = mid if not params else f"{mid}({','.join(f'{k}={v}' for k, v in sorted(params.items()))})"
        return MetricRef(m, params, key)


def _check_param(p: Param, v: Any) -> Any:
    if p.kind == "int":
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise InvalidSpec(f"parameter {p.name} must be an integer") from None
        if (p.lo is not None and v < p.lo) or (p.hi is not None and v > p.hi):
            raise InvalidSpec(f"parameter {p.name}={v} outside [{p.lo}, {p.hi}]")
        return v
    if v not in p.choices:
        raise InvalidSpec(f"parameter {p.name}={v!r} not in {list(p.choices)}")
    return v


@dataclass
class ResolvedWindow:
    kind: str                        # month | cy | fy | static
    periods: list                    # months 'YYYY-MM' or years int
    label: str
    notes: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    rows: list[dict[str, Any]]                   # {keys: {...}, values: {metric_key: v}, coverage: {...}}
    windows: dict[str, ResolvedWindow]           # fact id -> window
    lineage: dict[str, list[SourceRef]]          # metric_key -> sources
    classes: dict[str, str]                      # metric_key -> epistemic class
    notes: list[str]


class Engine:
    def __init__(self, con: duckdb.DuckDBPyConnection | None = None):
        self.con = con or connect()
        try:
            self.con.execute("SET enable_external_access = false")   # engine never needs files/network
        except Exception:
            pass
        self._avail: dict[str, list] = {}
        self._manifest = self.con.execute(
            "SELECT source_id, period, vintage_id FROM ingest_manifest WHERE selected ORDER BY 1, 2").fetchall()
        self.taf_last_historical = self.con.execute(
            "SELECT max(fiscal_year) FROM v_taf_enplanements WHERE record_type = 'historical'").fetchone()[0]

    # ------------------------------------------------------------ helpers used by custom metrics
    @staticmethod
    def month_list(months: list[str]) -> str:
        return ", ".join(f"DATE '{m}-01'" for m in months)

    @staticmethod
    def id_list(ids: list[int]) -> str:
        return ", ".join(str(int(i)) for i in ids) or "NULL"

    # ------------------------------------------------------------ coverage
    def available(self, fact_id: str) -> list:
        if fact_id not in self._avail:
            f = FACTS[fact_id]
            if f.time_kind == "month":
                src = f.sources[0]
                vals = [p for s, p, _ in self._manifest if s == src]
            elif f.time_kind in ("cy", "fy"):
                vals = [r[0] for r in self.con.execute(f"SELECT DISTINCT t FROM ({f.relation}) ORDER BY 1").fetchall()]
            else:
                vals = []
            self._avail[fact_id] = sorted(vals)
        return self._avail[fact_id]

    def resolve_window(self, window: dict[str, Any] | None, fact_id: str, latest_month: str | None = None) -> ResolvedWindow:
        f = FACTS[fact_id]
        w = dict(window or {"t12": True})
        if "cy" in w and "fy" in w:
            raise InvalidSpec("window sets both cy and fy; choose one calendar")
        avail = self.available(fact_id)
        if f.time_kind == "static":
            return ResolvedWindow("static", [], "current release", ["time window not applicable (static source)"])
        if f.time_kind == "month":
            if not avail:
                raise OutOfCoverage(f"no data loaded for {fact_id}")
            if "months" in w:
                months = sorted(w["months"])
            elif "start" in w or "end" in w:
                months = _months_between(w.get("start", avail[0]), w.get("end", avail[-1]))
            elif "cy" in w:
                months = _months_between(f"{int(w['cy'])}-01", f"{int(w['cy'])}-12")
            elif "fy" in w:
                months = _months_between(f"{int(w['fy']) - 1}-10", f"{int(w['fy'])}-09")
            elif w.get("t12"):
                end = _add_months(latest_month or avail[-1], -int(w.get("offset_months", 0)))
                months = _months_between(_add_months(end, -11), end)
            else:
                raise InvalidSpec(f"unsupported window {window}")
            missing = [m for m in months if m not in avail]
            if missing:
                raise OutOfCoverage(f"{fact_id}: window {months[0]}…{months[-1]} not fully covered",
                                    fact=fact_id, available=f"{avail[0]}…{avail[-1]}", missing=missing[:12])
            return ResolvedWindow("month", months, f"{months[0]}…{months[-1]}" if len(months) > 1 else months[0])
        # annual facts
        key = "cy" if f.time_kind == "cy" else "fy"
        notes = []
        if key in w:
            years = [int(w[key])]
        elif f"{key}_range" in w:
            a, b = w[f"{key}_range"]
            years = list(range(int(a), int(b) + 1))
        elif w.get("t12") or w.get("latest") or not w:
            if fact_id.startswith("taf"):
                raise InvalidSpec("TAF metrics need an explicit fiscal year, e.g. {\"fy\": 2030}")
            off = int(w.get("offset_months", 0))
            if off % 12:
                raise InvalidSpec(f"{fact_id} is annual: offset_months must be a multiple of 12")
            target = avail[-1] - off // 12                     # shift along the annual calendar (review: offset ignored)
            if target not in avail:
                raise OutOfCoverage(f"{fact_id}: {key.upper()} {target} not available", fact=fact_id,
                                    available=", ".join(str(y) for y in avail))
            years = [target]
            notes.append(f"{fact_id}: {key.upper()} {target} used for a T12/latest window (annual source)")
        elif "cy" in w and key == "fy" or "fy" in w and key == "cy":
            raise InvalidSpec(f"{fact_id} is reported in {key.upper()} — use {{\"{key}\": year}}")
        else:
            raise InvalidSpec(f"{fact_id} is annual ({key.upper()}); give {{\"{key}\": year}} or {{\"{key}_range\": [a, b]}}")
        missing = [y for y in years if y not in avail]
        if missing:
            raise OutOfCoverage(f"{fact_id}: {key.upper()} {missing} not available", fact=fact_id,
                                available=", ".join(str(y) for y in avail) if avail else "none")   # gaps visible
        if fact_id in STOCK_FACTS and len(years) > 1:
            raise InvalidSpec(f"{fact_id} values are stocks (e.g. population) and cannot be summed over years; "
                              f"use a single year or a pct_change transform")
        lab = f"{key.upper()}{years[0]}" if len(years) == 1 else f"{key.upper()}{years[0]}–{years[-1]}"
        return ResolvedWindow(key, years, lab, notes)

    def common_latest_month(self, facts: set[str]) -> str | None:
        monthly = [f for f in facts if FACTS[f].time_kind == "month"]
        if not monthly:
            return None
        return min(self.available(f)[-1] for f in monthly)

    # ------------------------------------------------------------ lineage
    def lineage(self, fact_id: str, win: ResolvedWindow) -> list[SourceRef]:
        f = FACTS[fact_id]
        refs = []
        for src in f.sources:
            rows = [(p, v) for s, p, v in self._manifest if s == src]
            want = {str(p) for p in win.periods}
            if f.time_kind == "cy" and src == "faa_enplanements":   # CY y is published in workbook y (or y+1's prior column)
                want |= {str(int(p) + 1) for p in win.periods}
            hit = [(p, v) for p, v in rows if p in want] if f.time_kind in ("month", "cy", "fy") else []
            use = hit or rows
            refs.append(SourceRef(src, sorted({p for p, _ in use}), sorted({v for _, v in use})))
        return refs

    # ------------------------------------------------------------ SQL compilation
    @staticmethod
    def _key_expr(dim: str, fact_id: str) -> str:
        f = FACTS[fact_id]
        if dim == "airport":
            return "r.airport_id"
        if dim in AIRPORT_ATTR_DIMS:
            return f"a.{dim}"
        if dim in TIME_DIMS:
            if f.time_kind == "month":
                return {"month": "strftime(r.t, '%Y-%m')", "year": "year(r.t)",
                        "fiscal_year": "CASE WHEN month(r.t) >= 10 THEN year(r.t) + 1 ELSE year(r.t) END"}[dim]
            if (f.time_kind == "cy" and dim == "year") or (f.time_kind == "fy" and dim == "fiscal_year"):
                return "r.t"
            raise InvalidSpec(f"cannot group {fact_id} ({f.time_kind}) by {dim}")
        if dim in f.dims:
            return f"({f.dims[dim]})"
        raise InvalidSpec(f"dimension '{dim}' not available for {fact_id}",
                          available=["airport", *AIRPORT_ATTR_DIMS, *TIME_DIMS, *f.dims])

    def _filter_sql(self, filters: dict[str, Any], fact_id: str) -> str:
        f = FACTS[fact_id]
        parts = []
        for dim, val in (filters or {}).items():
            if dim in AIRPORT_ATTR_DIMS:
                col = f"a.{dim}"
            elif dim in f.dims:
                col = f"({f.dims[dim]})"
            else:
                raise InvalidSpec(f"filter '{dim}' not supported by {fact_id}", available=[*AIRPORT_ATTR_DIMS, *f.dims])
            vals = val if isinstance(val, list) else [val]
            lit = ", ".join("TRUE" if v is True else "FALSE" if v is False else
                            str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'" for v in vals)
            parts.append(f"{col} IN ({lit})")
        return " AND ".join(parts) or "TRUE"

    def _time_sql(self, fact_id: str, win: ResolvedWindow) -> str:
        if win.kind == "static":
            return "TRUE"
        if win.kind == "month":
            return f"r.t IN ({self.month_list(win.periods)})"
        return f"r.t IN ({', '.join(str(y) for y in win.periods)})"

    def _run_fact(self, fact_id: str, measures: dict[str, tuple[Measure, dict]], ids: list[int],
                  group_by: list[str], filters: dict, win: ResolvedWindow) -> dict[tuple, dict[str, Any]]:
        f = FACTS[fact_id]
        keys = [self._key_expr(d, fact_id) for d in group_by]
        key_sel = [f"{k} AS k{i}" for i, k in enumerate(keys)]
        aggs = [f"{ms.agg.format(**bp)} AS \"{name}\"" for name, (ms, bp) in measures.items()]
        base = f"""({f.relation}) r JOIN (SELECT unnest([{self.id_list(ids)}]) AS airport_id) e USING (airport_id)
                   LEFT JOIN _attr a USING (airport_id)
                   WHERE {self._time_sql(fact_id, win)} AND {self._filter_sql(filters, fact_id)}"""
        if f.area_key:   # distinct areas so that two airports in one CBSA are counted once
            inner = f"SELECT DISTINCT {', '.join(key_sel + ['r.area', 'r.t', 'r.population', 'r.personal_income_usd'])} FROM {base}"
            sql = f"SELECT {', '.join([f'k{i}' for i in range(len(keys))] + aggs)} FROM ({inner}) GROUP BY ALL"
        else:
            sql = f"SELECT {', '.join(key_sel + aggs)} FROM {base} GROUP BY ALL" if keys else f"SELECT {', '.join(aggs)} FROM {base}"
        out = {}
        for row in self.con.execute(sql).fetchall():
            k, v = tuple(row[:len(keys)]), row[len(keys):]
            out[k] = dict(zip(measures, v))
        return out

    def _ensure_attr(self):
        self.con.execute("""CREATE TEMP VIEW IF NOT EXISTS _attr AS
            SELECT d.airport_id, d.current_code AS code, d.state_abr AS state, d.census_division, d.census_region,
                   f.faa_hub_class AS hub_class, x.cbsa_title AS cbsa
            FROM dim_airport d LEFT JOIN dim_airport_faa f USING (airport_id)
            LEFT JOIN xref_airport_county x USING (airport_id)""")

    # ------------------------------------------------------------ public
    def evaluate(self, metric_refs: list[Any], airport_ids: list[int], window: dict | None = None,
                 group_by: list[str] | None = None, filters: dict | None = None,
                 attach_coverage: bool = True) -> EvalResult:
        if not airport_ids:
            raise InsufficientData("empty airport set")
        if len(airport_ids) > 3000:
            raise InvalidSpec("airport set too large")
        group_by = list(group_by or [])
        refs = [r if isinstance(r, MetricRef) else MetricRef.parse(r) for r in metric_refs]
        if not refs:
            raise InvalidSpec("no metrics requested")
        self._ensure_attr()
        for r in refs:
            if r.metric.expr == "custom" and any(d != "airport" for d in group_by):
                raise InvalidSpec(f"{r.metric.id} is non-additive and supports only group_by ['airport']")
            if r.metric.expr == "custom" and not group_by and len(airport_ids) > 1:
                raise InvalidSpec(f"{r.metric.id} is non-additive: group_by ['airport'] required for several airports")
        t12 = (window or {"t12": True}).get("t12")
        notes: list[str] = []
        ref_windows: dict[str, dict[str, ResolvedWindow]] = {}
        buckets: dict[tuple, dict[str, tuple[Measure, dict]]] = {}   # (fact, periods) -> measures
        alias: dict[str, dict[str, str]] = {}
        for r in refs:
            mm = metric_measures(r.metric, r.params)
            facts_r = {ms.fact for ms, _ in mm.values()} or {r.metric.custom_fact}
            latest = self.common_latest_month(facts_r) if t12 else None   # align only within a metric
            ref_windows[r.key] = {f: self.resolve_window(window, f, latest) for f in facts_r}
            if facts_r & STOCK_FACTS and any(len(w.periods) > 1 for f, w in ref_windows[r.key].items()
                                             if f not in STOCK_FACTS and w.kind in ("cy", "fy")):
                raise InvalidSpec(f"{r.metric.id} combines a stock (single release) with a multi-year flow window; "
                                  "use a single year")
            alias[r.key] = {}
            for nm, (ms, bp) in mm.items():
                w = ref_windows[r.key][ms.fact]
                bkey = (ms.fact, tuple(w.periods))
                uniq = ms.id + ("" if not bp else "__" + "_".join(f"{k}{v}" for k, v in sorted(bp.items()) if k != "scope_sql")
                                + f"_{r.params.get('scope', '')}") + f"@{abs(hash(bkey)) % 10**8}"
                buckets.setdefault(bkey, {})[uniq] = (ms, bp)
                alias[r.key][nm] = uniq
        for w in (w for ws in ref_windows.values() for w in ws.values()):
            notes += [n for n in w.notes if n not in notes]
        labels = {w.label for ws in ref_windows.values() for f, w in ws.items() if w.kind == "month"}
        if len(labels) > 1:
            notes.append("monthly sources have different latest months; each finding states its own window: "
                         + "; ".join(sorted(labels)))
        data: dict[tuple, dict[str, Any]] = {}
        for (fact_id, periods), ms in buckets.items():
            win = next(w for ws in ref_windows.values() for f, w in ws.items() if f == fact_id and tuple(w.periods) == periods)
            for k, vals in self._run_fact(fact_id, ms, airport_ids, group_by, filters or {}, win).items():
                data.setdefault(k, {}).update(vals)
        custom_vals: dict[str, dict] = {}
        for r in refs:
            if r.metric.expr == "custom":
                months = ref_windows[r.key][r.metric.custom_fact].periods
                custom_vals[r.key] = r.metric.custom(self, airport_ids, months, r.params)
                if group_by == ["airport"]:
                    for aid in custom_vals[r.key]:
                        data.setdefault((aid,), {})
                elif not group_by:
                    data.setdefault((), {})
        # On-Time coverage over the months shared by On-Time and T-100 (attached, labelled)
        cov_rows, cov_label = {}, None
        ontime_refs = [r for r in refs if any(FACTS[f].sources == ("bts_ontime",) for f in ref_windows[r.key])]
        if ontime_refs and attach_coverage and filters:
            notes.append("On-Time coverage not attached: it is defined for unfiltered airport traffic")
        if ontime_refs and attach_coverage and not filters and all(d in ("airport", *AIRPORT_ATTR_DIMS) for d in group_by):
            ot_months = set(next(w for f, w in ref_windows[ontime_refs[0].key].items() if f.startswith("ontime")).periods)
            shared = sorted(ot_months & set(self.available("t100_dep")))
            if shared:
                cov = self.evaluate(["ontime_coverage"], airport_ids, {"months": shared}, group_by, filters=None,
                                    attach_coverage=False)
                cov_rows = {tuple(row["keys"].get(d) for d in group_by): row["values"]["ontime_coverage"] for row in cov.rows}
                cov_label = f"{shared[0]}…{shared[-1]}"
            else:
                notes.append("On-Time coverage not computable: no months shared with T-100 in this window")
        rows = []
        for k in sorted(data, key=lambda t: tuple("" if x is None else str(x) for x in t)):
            vals = data[k]
            out = {}
            for r in refs:
                if r.metric.expr == "custom":
                    aid = k[0] if group_by == ["airport"] else airport_ids[0]
                    out[r.key] = custom_vals[r.key].get(aid)
                else:
                    out[r.key] = eval_expr(metric_expr(r.metric), {nm: vals.get(u) for nm, u in alias[r.key].items()})
            cov = cov_rows.get(k) if cov_rows else None
            rows.append({"keys": dict(zip(group_by, k)), "values": out,
                         "ontime_coverage": None if cov is None else {"ratio": cov, "window": cov_label}})
        windows = {f"{r.key}|{f}": w for r in refs for f, w in ref_windows[r.key].items()}
        lineage, classes = {}, {}
        for r in refs:
            fs = set(ref_windows[r.key])
            lineage[r.key] = [s for f in sorted(fs) for s in self.lineage(f, ref_windows[r.key][f])]
            cls = r.metric.epistemic_class
            if fs & {"taf_enp", "taf_ops"}:
                yrs = [y for f in fs if f.startswith("taf") for y in ref_windows[r.key][f].periods]
                cls = "observed" if yrs and max(yrs) <= self.taf_last_historical else "forecast"
                if yrs and min(yrs) <= self.taf_last_historical < max(yrs):
                    notes.append(f"{r.metric.id}: fiscal-year range mixes TAF history (≤FY{self.taf_last_historical}) and "
                                 "forecast years; the total is labelled forecast")
            classes[r.key] = cls
        return EvalResult(rows, windows, lineage, classes, notes)
