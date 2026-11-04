"""Read-only access to the built database (the interface for analytics/agent layers)."""
from __future__ import annotations

import duckdb

from .config import Paths, get_paths


def connect(paths: Paths | None = None, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    paths = paths or get_paths()
    if not paths.db_file.exists():
        raise FileNotFoundError(f"{paths.db_file} not found — run `python -m airport_data build`")
    return duckdb.connect(str(paths.db_file), read_only=read_only)
