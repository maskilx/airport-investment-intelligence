"""Filesystem layout. Override the root with AIRPORT_DATA_DIR (used by tests)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def raw(self) -> Path:          # original files, vintaged, committed (the seed)
        return self.root / "raw"

    @property
    def manifest(self) -> Path:     # fetch event log + validation results (committed)
        return self.root / "manifest"

    @property
    def curated(self) -> Path:      # hand-maintained, cited tables (committed)
        return self.root / "curated"

    @property
    def reference(self) -> Path:    # static code lists (committed)
        return self.root / "reference"

    @property
    def db_dir(self) -> Path:       # rebuildable, git-ignored
        return self.root / "db"

    @property
    def db_file(self) -> Path:
        return self.db_dir / "airport.duckdb"

    @property
    def tmp(self) -> Path:
        return self.root / "tmp"


def get_paths(root: str | os.PathLike | None = None) -> Paths:
    root = root or os.environ.get("AIRPORT_DATA_DIR") or (REPO_ROOT / "data")
    return Paths(Path(root))
