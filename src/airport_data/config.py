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

    @property
    def app(self) -> Path:          # runtime state: conversations, model usage log (git-ignored)
        return self.root / "app"


def load_env(path: str | os.PathLike | None = None) -> list[str]:
    """Minimal .env loader (no dependency): KEY=VALUE lines from <repo>/.env, never overriding variables already set in
    the environment. Returns the names it set (values are never logged)."""
    p = Path(path) if path else REPO_ROOT / ".env"
    if not p.is_file():
        return []
    set_ = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip().removeprefix("export ").strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
            set_.append(k)
    return set_


KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT = "airport-investment-intelligence", "GEMINI_API_KEY"


def keychain_secret() -> str | None:
    """Gemini key from the macOS Keychain (written by scripts/configure-gemini-key.sh). The secret comes back on the
    `security` tool's stdout; it is never part of a command line or a log."""
    import subprocess
    import sys
    if sys.platform != "darwin":
        return None
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    v = r.stdout.strip()
    return v if r.returncode == 0 and v else None


def load_gemini_key() -> str | None:
    """Environment / .env first, then the Keychain. Only called when Gemini mode is configured."""
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or keychain_secret()


def get_paths(root: str | os.PathLike | None = None) -> Paths:
    root = root or os.environ.get("AIRPORT_DATA_DIR") or (REPO_ROOT / "data")
    return Paths(Path(root))
