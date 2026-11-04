"""Source adapter interface.

To add a source: subclass `Source`, declare metadata + `tables`, implement
`available_periods` / `fetch` / `load`, optionally `checks`, and register it in
`sources/__init__.py`. Nothing else in the pipeline needs to change.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from ..rawstore import RawFile, Vintage
from ..validation import CheckResult, ValidationReport

if TYPE_CHECKING:  # pragma: no cover
    import duckdb
    from ..http import HttpClient


@dataclass(frozen=True)
class TableSpec:
    """Declarative contract for one table a source produces."""
    name: str
    description: str
    required_columns: tuple[str, ...] = ()
    not_null: tuple[str, ...] = ()
    unique_key: tuple[str, ...] = ()
    unique_key_blocking: bool = False
    non_negative: tuple[str, ...] = ()
    min_rows: int | None = 1          # per period (per vintage)
    max_rows: int | None = None
    # types for the empty placeholder created when a source has no valid data yet, so that
    # downstream SQL still binds (graceful degradation: empty results, not errors)
    placeholder_types: tuple[tuple[str, str], ...] = ()


@dataclass
class FetchResult:
    files: list[RawFile]
    url: str
    request: dict[str, Any] = field(default_factory=dict)       # params needed to reproduce the request
    response_headers: dict[str, str] = field(default_factory=dict)
    source_reported: dict[str, Any] = field(default_factory=dict)  # e.g. "latest available" banner text


class Source(ABC):
    # ---- metadata (override as class attributes) ----
    id: str
    title: str
    publisher: str
    license: str
    homepage: str
    period_kind: str          # "month" (YYYY-MM) | "year" (YYYY) | "snapshot" (YYYY-MM-DD) | "version"
    cadence: str              # "monthly" | "annual" | "nightly" | "manual"
    expected_lag_days: int    # typical publication lag after the period ends
    tables: tuple[TableSpec, ...]
    notes: str = ""
    # "accumulate": every period is a distinct slice of history (monthly/annual facts).
    # "latest": each period is a full replacement (snapshots, forecast releases) -> only the newest
    #           valid period is loaded; older ones stay archived (prevents double counting).
    history_mode: str = "accumulate"

    # ---- network ----
    @abstractmethod
    def available_periods(self, http: "HttpClient") -> list[str]:
        """Probe the publisher for periods currently available (cheap)."""

    @abstractmethod
    def fetch(self, period: str, http: "HttpClient") -> FetchResult:
        """Download the original file(s) for one period. No transformation."""

    # ---- integrity (pre-store, blocking) ----
    def integrity_errors(self, files: list[RawFile]) -> list[str]:
        errs = []
        for f in files:
            if not f.content:
                errs.append(f"{f.name}: empty")
            elif f.name.lower().endswith((".zip", ".xlsx")):
                errs += [f"{f.name}: {e}" for e in zip_errors(f.content)]
            elif f.name.lower().endswith(".csv"):
                head = f.content[:4096].decode("utf-8", "replace")
                if "<html" in head.lower():
                    errs.append(f"{f.name}: looks like an HTML error page, not CSV")
        return errs

    # ---- load (raw -> staging tables in the build DB) ----
    @abstractmethod
    def load(self, con: "duckdb.DuckDBPyConnection", v: Vintage, staging: dict[str, str], tmp: Path) -> None:
        """Create each staging table named staging[spec.name] from the vintage's files."""

    def checks(self, con: "duckdb.DuckDBPyConnection", v: Vintage, staging: dict[str, str]) -> Iterable[CheckResult]:
        return ()

    # ---- helpers ----
    def table(self, name: str) -> TableSpec:
        return next(t for t in self.tables if t.name == name)

    def describe(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in
                ("id", "title", "publisher", "license", "homepage", "period_kind", "cadence", "expected_lag_days", "notes")}


# ---------------------------------------------------------------- utilities
def zip_errors(content: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            bad = z.testzip()
            return [f"CRC failure in member {bad}"] if bad else []
    except zipfile.BadZipFile as e:
        return [f"not a valid zip: {e}"]


def snake(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z]+", "_", name.strip())
    s = s.replace("Dayof", "Day_Of")                      # BTS "DayofMonth"/"DayOfWeek"
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)      # "CRSDep" -> "CRS_Dep"
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return re.sub(r"_+", "_", s).strip("_").lower()


def month_periods(start: str, end: str) -> list[str]:
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def extract_member(v: Vintage, archive: str, pattern: str, tmp: Path) -> Path:
    """Extract one member (regex on name) from a zip in the vintage to tmp."""
    with zipfile.ZipFile(v.file(archive)) as z:
        names = [n for n in z.namelist() if re.search(pattern, n)]
        if len(names) != 1:
            raise ValueError(f"{archive}: expected one member matching {pattern!r}, found {names}")
        tmp.mkdir(parents=True, exist_ok=True)
        out = tmp / f"{v.source_id}_{v.period}_{v.vintage_id}_{Path(names[0]).name}".replace(" ", "_")
        with z.open(names[0]) as src, open(out, "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
        return out


def csv_header_snake(path: Path) -> dict[str, str]:
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        header = next(csv.reader(f))
    return {h: snake(h) for h in header if h.strip()}


def load_csv_snake(con: "duckdb.DuckDBPyConnection", path: Path, table: str,
                   types: dict[str, str] | None = None, all_varchar: bool = False) -> None:
    """Load a CSV verbatim (all columns) with snake_case names.

    Column types are auto-detected over the whole file unless overridden."""
    mapping = csv_header_snake(path)
    opts = ["header=true", "sample_size=-1", "null_padding=true"]
    if all_varchar:
        opts.append("all_varchar=true")
    if types:
        inv = {v: k for k, v in mapping.items()}
        tdict = ", ".join(f"'{inv[c]}': '{t}'" for c, t in types.items() if c in inv)
        if tdict:
            opts.append(f"types={{{tdict}}}")
    select = ", ".join(f'"{orig}" AS "{new}"' for orig, new in mapping.items())
    con.execute(f"CREATE OR REPLACE TABLE \"{table}\" AS SELECT {select} FROM read_csv('{path}', {', '.join(opts)})")


def rows_to_table(con: "duckdb.DuckDBPyConnection", table: str, header: list[str], rows: Iterable[tuple], tmp: Path,
                  types: dict[str, str] | None = None) -> None:
    """Materialise python rows (e.g. from openpyxl) via a temp CSV (keeps deps minimal)."""
    tmp.mkdir(parents=True, exist_ok=True)
    p = tmp / f"{table}.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if x is None else (x.strip() if isinstance(x, str) else x) for x in r])
    load_csv_snake(con, p, table, types=types)
    p.unlink()


def today() -> date:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).date()   # UTC: snapshot periods must not depend on local TZ
