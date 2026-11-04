"""Immutable, vintaged archive of original source files.

Layout:
    raw/<source_id>/<period>/<vintage_id>/<original files...>
    raw/<source_id>/<period>/<vintage_id>/meta.json      (written last = commit marker)

Rules:
  * A vintage is never modified or deleted by code. Files are made read-only.
  * A new vintage is created only when the content differs (sha256) from the
    newest existing vintage of the same (source, period). Identical re-downloads
    are logged as `unchanged` events instead.
  * Directories without meta.json are incomplete writes and are ignored.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

META = "meta.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class RawFile:
    name: str
    content: bytes


@dataclass(frozen=True)
class Vintage:
    source_id: str
    period: str
    vintage_id: str
    path: Path
    meta: dict[str, Any]

    def file(self, name: str) -> Path:
        return self.path / name

    @property
    def files(self) -> list[dict[str, Any]]:
        return self.meta["files"]

    @property
    def content_sha256(self) -> str:
        """Hash over all files (name + sha), identifies the vintage's content."""
        return self.meta["content_sha256"]


def _content_hash(files: list[dict[str, Any]]) -> str:
    joined = "\n".join(f"{f['name']}:{f['sha256']}" for f in sorted(files, key=lambda f: f["name"]))
    return sha256_bytes(joined.encode())


class RawStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    # ---------- read ----------
    def sources(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir()) if self.root.exists() else []

    def periods(self, source_id: str) -> list[str]:
        d = self.root / source_id
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []

    def vintages(self, source_id: str, period: str) -> list[Vintage]:
        """Oldest first."""
        d = self.root / source_id / period
        out = []
        if d.exists():
            for v in sorted(d.iterdir()):
                m = v / META
                if v.is_dir() and m.exists():
                    try:
                        meta = json.loads(m.read_text())
                    except (ValueError, OSError):
                        continue  # unreadable meta = incomplete vintage; ignored, never fatal
                    out.append(Vintage(source_id, period, v.name, v, meta))
        return out

    def latest(self, source_id: str, period: str) -> Vintage | None:
        vs = self.vintages(source_id, period)
        return vs[-1] if vs else None

    # ---------- write ----------
    def put(self, source_id: str, period: str, files: list[RawFile], fetch_meta: dict[str, Any]) -> tuple[Vintage, bool]:
        """Store files as a new vintage unless identical to the newest one.

        Returns (vintage, created)."""
        if not files:
            raise ValueError("no files to store")
        entries = [{"name": f.name, "sha256": sha256_bytes(f.content), "bytes": len(f.content)} for f in files]
        content_sha = _content_hash(entries)
        latest = self.latest(source_id, period)
        if latest is not None and latest.content_sha256 == content_sha and not self.verify(latest):
            return latest, False   # identical AND the stored copy is still intact (else store a fresh vintage)

        vintage_id = utc_now().replace("-", "").replace(":", "")
        vdir = self.root / source_id / period / vintage_id
        n = 1
        while vdir.exists():  # same-second collision
            vdir = self.root / source_id / period / f"{vintage_id}_{n}"
            n += 1
        vdir.mkdir(parents=True)
        for f in files:
            tmp = vdir / (f.name + ".part")
            tmp.write_bytes(f.content)
            os.replace(tmp, vdir / f.name)
            os.chmod(vdir / f.name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        meta = {
            "source_id": source_id,
            "period": period,
            "vintage_id": vdir.name,
            "stored_at": utc_now(),
            "files": entries,
            "content_sha256": content_sha,
            "supersedes": latest.vintage_id if latest else None,
            **fetch_meta,
        }
        tmp_meta = vdir / (META + ".part")
        tmp_meta.write_text(json.dumps(meta, indent=2, sort_keys=True))
        os.replace(tmp_meta, vdir / META)          # atomic commit marker
        os.chmod(vdir / META, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return Vintage(source_id, period, vdir.name, vdir, meta), True

    def verify(self, v: Vintage) -> list[str]:
        """Re-hash files on disk against meta (detects corruption / tampering)."""
        errors = []
        for f in v.files:
            p = v.file(f["name"])
            if not p.exists():
                errors.append(f"missing file {f['name']}")
            elif sha256_file(p) != f["sha256"]:
                errors.append(f"checksum mismatch {f['name']}")
        return errors
