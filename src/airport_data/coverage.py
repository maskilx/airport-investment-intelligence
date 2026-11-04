"""Data-coverage assertions: does the DB actually contain what the questions need?

Requirements are declarative (config/coverage.toml) and generic — they describe
populations, periods and fields, not specific questions — so new requirements
are added by editing config, not code. Check types:

  contiguous_months   source_id, min_months           selected months have no gaps and span >= N
  field_completeness  table, columns, max_null_rate, [where]
  population_covered  population_sql, covered_sql, min_share   (both return one key column)
  sql_assert          sql -> (passed BOOLEAN, detail VARCHAR)
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT

DEFAULT = REPO_ROOT / "config" / "coverage.toml"


@dataclass
class CoverageResult:
    id: str
    passed: bool
    detail: str
    purpose: str = ""


def _contiguous(con, req) -> CoverageResult:
    ps = [r[0] for r in con.execute("SELECT DISTINCT period FROM ingest_manifest WHERE source_id = ? AND selected "
                                    "ORDER BY 1", [req["source_id"]]).fetchall()]
    if not ps:
        return CoverageResult(req["id"], False, "no periods loaded")
    idx = [int(p[:4]) * 12 + int(p[5:7]) for p in ps]
    gaps = [ps[i] for i in range(1, len(idx)) if idx[i] - idx[i - 1] != 1]
    ok = not gaps and len(ps) >= req["min_months"] if req.get("contiguous", True) else len(ps) >= req["min_months"]
    return CoverageResult(req["id"], ok, f"{len(ps)} months {ps[0]}..{ps[-1]}; gaps before {gaps or 'none'}")


def _completeness(con, req) -> CoverageResult:
    where = f"WHERE {req['where']}" if req.get("where") else ""
    n = con.execute(f"SELECT count(*) FROM {req['table']} {where}").fetchone()[0]
    if n == 0:
        return CoverageResult(req["id"], False, "0 rows in scope")
    worst = []
    for c in req["columns"]:
        nulls = con.execute(f'SELECT count(*) FROM {req["table"]} {where} {"AND" if where else "WHERE"} "{c}" IS NULL').fetchone()[0]
        worst.append((nulls / n, c))
    worst.sort(reverse=True)
    ok = worst[0][0] <= req.get("max_null_rate", 0.0)
    return CoverageResult(req["id"], ok, f"{n} rows; worst null rate {worst[0][1]}={worst[0][0]:.3%}")


def _population(con, req) -> CoverageResult:
    pop = {r[0] for r in con.execute(req["population_sql"]).fetchall()}
    cov = {r[0] for r in con.execute(req["covered_sql"]).fetchall()}
    if not pop:
        return CoverageResult(req["id"], False, "empty population")
    share = len(pop & cov) / len(pop)
    missing = sorted(pop - cov)
    return CoverageResult(req["id"], share >= req["min_share"],
                          f"{len(pop & cov)}/{len(pop)} = {share:.1%} (min {req['min_share']:.0%}); "
                          f"missing: {missing[:15]}{' …' if len(missing) > 15 else ''}")


def _sql(con, req) -> CoverageResult:
    passed, detail = con.execute(req["sql"]).fetchone()
    return CoverageResult(req["id"], bool(passed), str(detail))


CHECKS = {"contiguous_months": _contiguous, "field_completeness": _completeness,
          "population_covered": _population, "sql_assert": _sql}


def run_coverage(con, config: Path = DEFAULT) -> list[CoverageResult]:
    reqs = tomllib.loads(Path(config).read_text())["requirement"]
    out = []
    for r in reqs:
        try:
            res = CHECKS[r["type"]](con, r)
        except Exception as e:
            res = CoverageResult(r["id"], False, f"error: {type(e).__name__}: {e}")
        res.purpose = r.get("purpose", "")
        out.append(res)
    return out
