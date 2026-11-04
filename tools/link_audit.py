"""Audit every external link the product or its docs show (docs/link-audit.md is written from this output).

    .venv/bin/python tools/link_audit.py > eval/runs/link_audit.json

For each distinct URL: GET with a small Range (first bytes only), follow redirects, record HTTP status, final URL,
content type, length, HTML <title>, and the file signature (zip / xlsx / pdf / csv / xml). HTTP 200 is NOT treated as
proof: the report records what the destination actually is so a human can judge relevance. No credentials are sent.
"""
from __future__ import annotations

import csv
import glob
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def inventory() -> dict[str, set[str]]:
    import duckdb

    from airport_data.config import get_paths
    c = duckdb.connect(str(get_paths().db_file), read_only=True)
    out: dict[str, set[str]] = {}

    def add(url, where):
        if url and url.startswith("http"):
            out.setdefault(url, set()).add(where)
    for sid, hp in c.execute("SELECT id, homepage FROM source_catalog").fetchall():
        add(hp, f"source catalog homepage ({sid}) - inspector 'Dataset page'")
    for sid, url in c.execute("SELECT DISTINCT source_id, url FROM ingest_manifest WHERE selected").fetchall():
        add(url, f"build manifest fetch URL ({sid}) - inspector 'raw file'")
    for r in csv.DictReader(open(ROOT / "data" / "curated" / "airport_constraints.csv")):
        add(r["source_url"], f"curated constraint source ({r['airport_iata']}: {r['item'][:40]})")
    for f in ["README.md", "ARCHITECTURE.md", *sorted(glob.glob(str(ROOT / "docs" / "*.md")))]:
        for u in re.findall(r"https?://[^\s)>\]\"'`]+", (ROOT / f).read_text() if not f.startswith("/") else Path(f).read_text()):
            add(u.rstrip(".,;"), f"doc link ({Path(f).name})")
    add("https://nasstatus.faa.gov/api/airport-status-information", "live API tool (live_airport_status)")
    return out


def sig(b: bytes) -> str:
    if b[:4] == b"PK\x03\x04":
        return "zip/xlsx"
    if b[:5] == b"%PDF-":
        return "pdf"
    if b.lstrip()[:5].lower() in (b"<!doc", b"<html"):
        return "html"
    if b.lstrip()[:1] == b"<":
        return "xml/html"
    if b[:1] in b"{[":
        return "json"
    return "text/other"


def check(url: str) -> dict:
    req = urllib.request.Request(url.replace(" ", "%20"), headers={"User-Agent": "Mozilla/5.0 (link audit; airport-intel)",
                                                                   "Range": "bytes=0-16383"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
            b = r.read(16384)
            title = ""
            if b"<title" in b.lower():
                m = re.search(rb"<title[^>]*>(.*?)</title>", b, re.I | re.S)
                title = re.sub(r"\s+", " ", m.group(1).decode("utf-8", "replace")).strip()[:120] if m else ""
            return {"status": r.status, "final_url": r.geturl(), "content_type": r.headers.get("Content-Type", ""),
                    "length": r.headers.get("Content-Range", "").split("/")[-1] or r.headers.get("Content-Length", ""),
                    "signature": sig(b), "title": title}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "final_url": e.geturl() if hasattr(e, "geturl") else url, "error": str(e.reason)}
    except Exception as e:
        return {"status": None, "error": f"{type(e).__name__}: {str(e)[:120]}"}


if __name__ == "__main__":
    inv = inventory()
    res = [{"url": u, "used_in": sorted(inv[u]), **check(u)} for u in sorted(inv)]
    print(json.dumps(res, indent=1))
