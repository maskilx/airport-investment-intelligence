"""Tool surface for any LLM agent (framework-agnostic): name, description, JSON schema, handler.

Every handler returns JSON-serialisable data. Errors are returned as structured objects
({"error": code, "message": ...}) so the model can recover (ask, narrow, or report not_established).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .analysis import OPS, TRANSFORMS, Context, _new, run_analysis
from .engine import Engine
from .evidence import AnalyticsError, EvidenceStore, InvalidSpec, SourceRef
from .render import render, validate
from .resolver import Resolver
from .semantic import AIRPORT_ATTR_DIMS, CATALOG_VERSION, FACTS, MEASURES, METRICS

SQL_VIEWS = ("v_t100_segment", "v_ontime_flight", "v_atads_airport_ops", "v_taf_enplanements", "v_taf_operations",
             "v_faa_enplanements_annual", "v_faa_grant", "v_airport_investment_records", "v_cbsa_econ_annual",
             "v_county_econ_annual", "v_airport_area_econ", "v_source_period_status", "v_airport_month_activity",
             "dim_airport", "dim_airport_faa", "xref_airport_county", "npias_airport", "curated_constraint")
VIEW_SOURCES = {"v_t100_segment": "bts_t100_segment", "v_ontime_flight": "bts_ontime", "v_atads_airport_ops": "faa_atads_ops",
                "v_taf_enplanements": "faa_taf", "v_taf_operations": "faa_taf", "v_faa_enplanements_annual": "faa_enplanements",
                "v_faa_grant": "faa_grants", "npias_airport": "faa_npias", "v_cbsa_econ_annual": "bea_cainc1",
                "v_county_econ_annual": "bea_cainc1", "curated_constraint": "curated_constraints"}


@dataclass
class Tool:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[["Session", dict], Any]


class Session:
    def __init__(self, engine: Engine | None = None):
        self.engine = engine or Engine()
        self.ctx = Context(self.engine, Resolver(self.engine.con), EvidenceStore())

    def call(self, name: str, args: dict[str, Any]) -> Any:
        tool = TOOLS.get(name)
        if not tool:
            return {"error": "unknown_tool", "message": name, "tools": list(TOOLS)}
        try:
            return tool.handler(self, args or {})
        except AnalyticsError as e:
            return e.to_dict()
        except (KeyError, TypeError, ValueError) as e:
            return {"error": "invalid_request", "message": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------------ handlers
def _resolve(s: Session, a: dict) -> Any:
    terms = a.get("terms") or []
    out = [s.ctx.resolver.resolve_term(str(t)).to_dict() for t in terms]
    if a.get("group"):
        g = s.ctx.resolver.group(a["group"])
        out.append({"group": a["group"], "airports": [s.ctx.resolver.code(i) for i in g["airport_ids"]],
                    "excluded_by_threshold": g["excluded"], "n_excluded": g["n_excluded"]})
    return {"resolutions": out}


def _catalog(s: Session, a: dict) -> Any:
    e = s.engine
    if a.get("metric"):
        m = METRICS.get(a["metric"])
        if not m:
            return {"error": "unknown_metric", "known": sorted(METRICS)}
        facts = sorted({MEASURES[n].fact for n in _names(m)} or {m.custom_fact})
        return {"id": m.id, "name": m.name, "unit": m.unit, "class": m.epistemic_class, "definition": m.definition,
                "formula": m.expr, "formula_version": m.formula_version, "params": [p.__dict__ for p in m.params],
                "facts": {f: {"description": FACTS[f].description, "time": FACTS[f].time_kind,
                              "dimensions": [*AIRPORT_ATTR_DIMS, *FACTS[f].dims],
                              "coverage": _cov(e, f)} for f in facts}}
    return {"catalog_version": CATALOG_VERSION, "ops": list(OPS), "transforms": list(TRANSFORMS),
            "metrics": {m.id: f"{m.name} [{m.unit}, {m.epistemic_class}]" for m in METRICS.values()},
            "group_by": ["airport", "month", "year", "fiscal_year", *AIRPORT_ATTR_DIMS, "carrier", "dest", "distance_band",
                         "international", "hour", "service_type", "record_type"],
            "entity_group_filters": ["state", "census_division", "census_region", "hub_class", "cbsa", "csa",
                                     "min_enplanements", "towered", "airports"],
            "windows": ['{"t12": true}', '{"t12": true, "offset_months": 12}', '{"start": "YYYY-MM", "end": "YYYY-MM"}',
                        '{"cy": 2025}', '{"fy": 2025}', '{"fy_range": [2021, 2025]}'],
            "coverage": {f: _cov(e, f) for f in FACTS if FACTS[f].time_kind != "static"},
            "screening_model": "op=screen: config/screening.toml (scenarios: base, equal_weights, demand_only, momentum_heavy)"}


def _names(m):
    from .semantic import expr_names
    return set() if m.expr in ("custom", "LONG_HAUL") else expr_names(m.expr)


def _cov(e: Engine, f: str) -> str:
    av = e.available(f)
    return f"{av[0]}…{av[-1]}" if av else "static"


def _run(s: Session, a: dict) -> Any:
    spec = a.get("spec") or a
    return run_analysis(spec, s.ctx)


def _derive(s: Session, a: dict) -> Any:
    op, ids = a.get("op"), a.get("findings") or []
    if op not in ("difference", "ratio", "pct_difference", "sum") or len(ids) < 2 or (op != "sum" and len(ids) != 2):
        raise InvalidSpec("derive: op ∈ difference|ratio|pct_difference (2 findings) or sum (≥2 findings)")
    fs = [s.ctx.store.get(i) for i in ids]
    if any(not isinstance(f.value, (int, float)) for f in fs):
        raise InvalidSpec("derive needs numeric findings with values")
    if op != "ratio" and len({f.unit for f in fs}) > 1:
        raise InvalidSpec(f"units differ ({[f.unit for f in fs]}); only ratio is allowed across units")
    v = {"difference": lambda: fs[0].value - fs[1].value,
         "ratio": lambda: None if fs[1].value == 0 else fs[0].value / fs[1].value,
         "pct_difference": lambda: None if fs[1].value == 0 else fs[0].value / fs[1].value - 1,
         "sum": lambda: sum(f.value for f in fs)}[op]()
    classes = {f.epistemic_class for f in fs}
    cls = next((c for c in ("hypothesis", "estimated", "forecast", "exploratory") if c in classes), "calculated")
    unit = fs[0].unit if op in ("difference", "sum") else "ratio"
    fmt = fs[0].fmt if op in ("difference", "sum") else "pct" if op == "pct_difference" else "ratio"
    f = _new(s.ctx, metric_id=f"derived:{op}", label=f"{op}({', '.join(f.id for f in fs)})", value=v, unit=unit, fmt=fmt,
             epistemic_class=cls, definition=f"{op} of " + " , ".join(f"[{f.label}]" for f in fs), formula_version="1",
             subject={"derived_from": ids}, window={"label": " | ".join(f.window.get("label", "") for f in fs)},
             sources=[x for f in fs for x in f.sources], caveats=list(dict.fromkeys(c for f in fs for c in f.caveats)),
             inputs=ids)
    return f.brief()


BANNED = re.compile(r"\b(attach|detach|copy|install|load|export|import|create|insert|update|delete|drop|alter|pragma|"
                    r"set|call|read_\w+|glob|getenv|system|from\s+'|httpfs)\b", re.I)


def _sql(s: Session, a: dict) -> Any:
    q = (a.get("sql") or "").strip().rstrip(";")
    if ";" in q or not re.match(r"^(select|with)\b", q, re.I) or BANNED.search(q):
        raise InvalidSpec("query_sql accepts one read-only SELECT/WITH over whitelisted views")
    refs = {t.lower() for t in re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", q, re.I)}
    ctes = {t.lower() for t in re.findall(r"\b([a-z_][a-z0-9_]*)\s+as\s*\(", q, re.I)}
    bad = refs - ctes - set(SQL_VIEWS)
    if bad:
        raise InvalidSpec(f"not whitelisted: {sorted(bad)}", allowed=list(SQL_VIEWS))
    cur = s.engine.con.execute(f"SELECT * FROM ({q}) LIMIT 201")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    srcs = [SourceRef(VIEW_SOURCES[v], [], []) for v in sorted(refs & set(VIEW_SOURCES))]
    out_rows = []
    for r in rows[:200]:
        cells = {}
        for c, v in zip(cols, r):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                f = _new(s.ctx, metric_id="exploratory_sql", label=f"{c} (exploratory query)", value=v, unit="", fmt="number",
                         epistemic_class="exploratory", definition=f"column {c} of: {q}", formula_version="1",
                         subject={"row": {k: str(x) for k, x in zip(cols, r) if not isinstance(x, (int, float)) or isinstance(x, bool)}},
                         window={"label": "as queried"}, sources=srcs,
                         caveats=["Exploratory SQL: definitions are not catalog metrics; verify before relying on it."])
                cells[c] = {"id": f.id, "value": v}
            else:
                cells[c] = None if v is None else str(v)
        out_rows.append(cells)
    return {"columns": cols, "rows": out_rows, "truncated": len(rows) > 200,
            "note": "exploratory: values are registered as findings with class 'exploratory'"}


def _compose(s: Session, a: dict) -> Any:
    ans = a.get("answer") or a
    errs = validate(ans, s.ctx.store)
    if errs:
        return {"error": "grounding_validation_failed", "errors": errs,
                "hint": "Put every number in a {F#} placeholder; cite findings in claims[].support; label hypotheses."}
    return render(ans, s.ctx.store)


def _finding(s: Session, a: dict) -> Any:
    f = s.ctx.store.get(a["id"])
    d = f.to_dict()
    if a.get("reproduce") and f.spec:
        r = run_analysis(dict(f.spec, op="aggregate"), s.ctx)
        d["reproduced"] = [x for x in r["findings"]][:3]
    return d


# ------------------------------------------------------------------ registry with JSON schemas
_METRIC_REF = {"oneOf": [{"type": "string"}, {"type": "object", "properties": {
    "id": {"type": "string"}, "params": {"type": "object"}, "window": {"type": "object"},
    "transform": {"type": "object", "properties": {"type": {"enum": list(TRANSFORMS)},
                                                   "compare_window": {"type": "object"}, "years": {"type": "number"}}}},
    "required": ["id"]}]}

TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("resolve_entities",
         "Resolve airport names/codes/cities/regions to airports or groups. Returns kind = airport | group | ambiguous | unknown "
         "with candidates and notes. Use before analysis when the user names places; ask the user when ambiguous "
         "(unless a contrast question makes the intended pair clear — then state the assumption).",
         {"type": "object", "properties": {"terms": {"type": "array", "items": {"type": "string"}},
                                           "group": {"type": "object"}}}, _resolve),
    Tool("describe_catalog",
         "List metrics, operators, transforms, dimensions, windows and data coverage, or describe one metric (formula, "
         "params, facts, coverage). Use to choose valid metric ids; never invent metric ids.",
         {"type": "object", "properties": {"metric": {"type": "string"}}}, _catalog),
    Tool("run_analysis",
         "Execute an analysis spec deterministically. Fields: op (" + "|".join(OPS) + "), metrics (ids or {id, params, window, "
         "transform}), entities ({airports:[...]} or {group:{...}}), group_by, window, filters, options "
         "(rank: criteria/scaling; correlate: x,y; anomaly: mode,z_threshold; forecast_vs_actual: fy,quantity; "
         "screen: scenario,min_enplanements). Returns findings with ids (F#) usable in the answer.",
         {"type": "object", "properties": {"spec": {"type": "object", "properties": {
             "op": {"enum": list(OPS)}, "metrics": {"type": "array", "items": _METRIC_REF},
             "entities": {"type": "object"}, "group_by": {"type": "array", "items": {"type": "string"}},
             "window": {"type": "object"}, "filters": {"type": "object"}, "options": {"type": "object"}},
             "required": ["op", "entities"]}}, "required": ["spec"]}, _run),
    Tool("derive",
         "Compute difference | ratio | pct_difference (two findings) or sum (≥2) of existing findings, producing a new "
         "finding with recorded inputs. Use instead of doing arithmetic yourself.",
         {"type": "object", "properties": {"op": {"enum": ["difference", "ratio", "pct_difference", "sum"]},
                                           "findings": {"type": "array", "items": {"type": "string"}}},
          "required": ["op", "findings"]}, _derive),
    Tool("query_sql",
         "Escape hatch: one read-only SELECT over whitelisted views (" + ", ".join(SQL_VIEWS) + "). Results are labelled "
         "'exploratory' and must be presented as such. Prefer run_analysis whenever a catalog metric exists.",
         {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}, _sql),
    Tool("get_finding",
         "Return full provenance of a finding (definition, sources, vintages, window, coverage, caveats, inputs, spec); "
         "reproduce=true re-executes its spec.",
         {"type": "object", "properties": {"id": {"type": "string"}, "reproduce": {"type": "boolean"}}, "required": ["id"]},
         _finding),
    Tool("compose_answer",
         "Validate and render the final answer. answer = {headline, body, claims:[{kind: fact|inference|hypothesis, text, "
         "support:[F#]}], assumptions:[...], limitations:[...]}. Write every number as a placeholder {F#} (or {F#.period}, "
         "{F#.label}); literal numbers are rejected. Evidence, methodology and caveats are appended automatically.",
         {"type": "object", "properties": {"answer": {"type": "object"}}, "required": ["answer"]}, _compose),
]}


def tool_schemas() -> list[dict[str, Any]]:
    """Anthropic/OpenAI-style tool definitions."""
    return [{"name": t.name, "description": t.description, "input_schema": t.schema} for t in TOOLS.values()]
