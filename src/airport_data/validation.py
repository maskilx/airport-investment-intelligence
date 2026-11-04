"""Validation engine.

Two severities:
  * error   -> blocking: the vintage is not promoted; the previous valid vintage
               of that period (if any) is used instead.
  * warning -> recorded and surfaced, never blocks.

Generic checks are driven by `TableSpec`; sources add their own via
`Source.checks()`. All checks run against *staging* tables inside the build DB.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    from .sources.base import TableSpec

RULES_VERSION = "1"


@dataclass
class CheckResult:
    name: str
    severity: str  # "error" | "warning"
    passed: bool
    detail: str = ""
    table: str | None = None
    value: Any = None


@dataclass
class ValidationReport:
    source_id: str
    period: str
    vintage_id: str
    rules_version: str = RULES_VERSION
    checks: list[CheckResult] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    schemas: dict[str, list[list[str]]] = field(default_factory=dict)

    def add(self, r: CheckResult) -> None:
        self.checks.append(r)

    @property
    def status(self) -> str:
        if any(not c.passed and c.severity == "error" for c in self.checks):
            return "fail"
        if any(not c.passed for c in self.checks):
            return "warn"
        return "pass"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status
        return d


def error(name: str, passed: bool, detail: str = "", table: str | None = None, value: Any = None) -> CheckResult:
    return CheckResult(name, "error", bool(passed), detail, table, value)


def warning(name: str, passed: bool, detail: str = "", table: str | None = None, value: Any = None) -> CheckResult:
    return CheckResult(name, "warning", bool(passed), detail, table, value)


def scalar(con: "duckdb.DuckDBPyConnection", sql: str, params: list | None = None) -> Any:
    row = con.execute(sql, params or []).fetchone()
    return row[0] if row else None


def table_schema(con: "duckdb.DuckDBPyConnection", table: str) -> list[list[str]]:
    return [[r[0], r[1]] for r in con.execute(f'DESCRIBE "{table}"').fetchall()]


def period_match_check(con, staging: str, period: str, year_col: str = "year", month_col: str = "month") -> CheckResult:
    """Blocking: every row's year/month equals the file's period (NULL-safe: NULL counts as a mismatch)."""
    y, m = map(int, period.split("-"))
    bad = scalar(con, f'SELECT count(*) FROM "{staging}" WHERE "{year_col}" IS DISTINCT FROM ? '
                      f'OR "{month_col}" IS DISTINCT FROM ?', [y, m])
    return error("period_matches_content", bad == 0, f"{bad} rows outside {period} (incl. NULL)", value=bad)


def generic_checks(con: "duckdb.DuckDBPyConnection", spec: "TableSpec", staging: str, rep: ValidationReport) -> None:
    schema = table_schema(con, staging)
    cols = {c for c, _ in schema}
    rep.schemas[spec.name] = schema
    n = scalar(con, f'SELECT count(*) FROM "{staging}"')
    rep.row_counts[spec.name] = n

    missing = [c for c in spec.required_columns if c not in cols]
    rep.add(error("required_columns", not missing, f"missing: {missing}" if missing else "all present", spec.name))
    if missing:
        return

    if spec.min_rows is not None or spec.max_rows is not None:
        lo, hi = spec.min_rows or 0, spec.max_rows
        ok = n >= lo and (hi is None or n <= hi)
        rep.add(error("row_count_in_range", ok, f"{n} rows, expected [{lo}, {hi if hi is not None else '∞'}]", spec.name, n))

    for c in spec.not_null:
        nulls = scalar(con, f'SELECT count(*) FROM "{staging}" WHERE "{c}" IS NULL')
        rep.add(error(f"not_null:{c}", nulls == 0, f"{nulls} null values", spec.name, nulls))

    if spec.unique_key:
        key = ", ".join(f'"{c}"' for c in spec.unique_key)
        dups = scalar(con, f'SELECT count(*) FROM (SELECT {key} FROM "{staging}" GROUP BY {key} HAVING count(*) > 1)')
        sev = error if spec.unique_key_blocking else warning
        rep.add(sev(f"unique_key:{'+'.join(spec.unique_key)}", dups == 0, f"{dups} duplicated keys", spec.name, dups))

    for c in spec.non_negative:
        neg = scalar(con, f'SELECT count(*) FROM "{staging}" WHERE "{c}" < 0')
        rep.add(error(f"non_negative:{c}", neg == 0, f"{neg} negative values", spec.name, neg))
