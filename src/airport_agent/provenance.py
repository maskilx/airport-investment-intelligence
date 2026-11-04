"""Provenance for the evidence inspector: everything here is read from the build's own catalog and manifest.

Links are never generated or guessed: `homepage` comes from the source registry (source_catalog) and the per-vintage
`url` is the exact URL the raw file was fetched from (ingest_manifest), alongside its sha256 and fetch time.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from airport_analytics.evidence import Finding


# How each source's raw file is actually obtained (verified in docs/link-audit.md). A link is labelled by what it opens:
# never call a form or an index page a "raw file".
ACCESS = {
    "bts_t100_segment": ("form", "BTS download form: the file is produced by submitting this form with the fields recorded "
                                 "in the raw archive (meta.json); the link opens the form, not the file"),
    "bts_lookups": ("form", "BTS lookup tables are downloaded through a form submission; there is no stable public link "
                            "to the file (the recorded URL redirects to the Transtats homepage)"),
    "faa_atads_ops": ("form", "FAA ATADS data is returned by the form's query endpoint (POST); the link opens the ATADS "
                              "query form, and the exact query is recorded in the raw archive"),
}
LINK_OVERRIDE = {"faa_atads_ops": "https://www.aspm.faa.gov/opsnet/sys/airport.asp",   # verified: ATADS form page
                 "bts_lookups": None}                                                  # verified: no stable file link
FILE_LINKS = {   # sources whose manifest URL is an index page: link the verified files instead
    "ourairports": [("airports.csv", "https://davidmegginson.github.io/ourairports-data/airports.csv"),
                    ("runways.csv", "https://davidmegginson.github.io/ourairports-data/runways.csv")],
}


def link_for(source_id: str, url: str | None) -> list[dict]:
    if not url or not url.startswith("http"):
        return []                                   # local curated/reference files: no web link
    if source_id in FILE_LINKS:
        return [{"label": f"raw file: {n}", "url": u, "kind": "file"} for n, u in FILE_LINKS[source_id]]
    kind, note = ACCESS.get(source_id, ("file", ""))
    if source_id in LINK_OVERRIDE:
        url = LINK_OVERRIDE[source_id]
        if url is None:
            return []
    return [{"label": "download form" if kind == "form" else "raw file", "url": url, "kind": kind, "note": note}]


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
        out = [dict(zip(("period", "vintage_id", "url", "stored_at", "sha256", "bytes", "validation"), r)) for r in rows]
        for v in out:
            v["links"] = link_for(source_id, v.get("url"))
        return out

    def finding(self, f: Finding) -> dict[str, Any]:
        d = f.to_dict()
        d["sources_detail"] = []
        for s in f.sources:
            meta = self.source(s.source_id) or {"id": s.source_id}
            vs = self.vintages(s.source_id, s.vintage_ids)
            d["sources_detail"].append({**meta, "periods": s.periods, "vintages": vs,
                                        "download_urls": list(dict.fromkeys(v["url"] for v in vs if v.get("url")))[:6],
                                        "access": ACCESS.get(s.source_id, ("file", ""))[0],
                                        "access_note": ACCESS.get(s.source_id, ("file", ""))[1]})
        d["kind"] = "internal_dataset"
        return json.loads(json.dumps(d, default=str))
