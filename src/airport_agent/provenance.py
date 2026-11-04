"""Provenance for the evidence inspector: everything here is read from the build's own catalog and manifest.

Links are never generated or guessed: `homepage` comes from the source registry (source_catalog) and the per-vintage
`url` is the exact URL the raw file was fetched from (ingest_manifest), alongside its sha256 and fetch time.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from airport_analytics.evidence import Finding


class Provenance:
    def __init__(self, con):
        self.con = con

    @lru_cache(maxsize=64)
    def source(self, source_id: str) -> dict[str, Any] | None:
        r = self.con.execute("SELECT id, title, publisher, license, homepage, period_kind, period_basis, cadence, notes "
                             "FROM source_catalog WHERE id = ?", [source_id]).fetchone()
        if not r:
            return None
        return dict(zip(("id", "title", "publisher", "license", "homepage", "period_kind", "period_basis", "cadence", "notes"), r))

    def vintages(self, source_id: str, vintage_ids: list[str], limit: int = 40) -> list[dict]:
        if not vintage_ids:
            return []
        rows = self.con.execute(
            "SELECT period, vintage_id, url, stored_at, content_sha256, bytes, validation_status FROM ingest_manifest "
            "WHERE source_id = ? AND vintage_id IN (SELECT unnest(?::VARCHAR[])) ORDER BY period", [source_id, vintage_ids[:limit]]
        ).fetchall()
        return [dict(zip(("period", "vintage_id", "url", "stored_at", "sha256", "bytes", "validation"), r)) for r in rows]

    def finding(self, f: Finding) -> dict[str, Any]:
        d = f.to_dict()
        d["sources_detail"] = []
        for s in f.sources:
            meta = self.source(s.source_id) or {"id": s.source_id}
            vs = self.vintages(s.source_id, s.vintage_ids)
            d["sources_detail"].append({**meta, "periods": s.periods, "vintages": vs,
                                        "download_urls": list(dict.fromkeys(v["url"] for v in vs if v.get("url")))[:6]})
        d["kind"] = "internal_dataset"
        return json.loads(json.dumps(d, default=str))
