"""Read-only access to the original downloaded files in the raw archive, for the evidence inspector.

Security model (the only way the browser can reach local files):
  * addressed by (source_id, period, vintage_id, file name) - never by a path;
  * each id must match a strict pattern, and the file name must be listed in that vintage's meta.json;
  * the resolved path must be a regular file inside data/raw (no symlinks, no '..', nothing else on disk:
    .env, the conversation database, logs and the DuckDB file are unreachable by construction);
  * previews are bounded (rows, columns, cell length, bytes read); files are never modified.
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,80}$")
PAGE_ROWS, MAX_COLS, MAX_CELL, MAX_PAGE = 50, 40, 160, 2000
MAX_SCAN_ROWS = 3_000_000          # a "find" scan stops here (bounded work per request)
FIND = re.compile(r"^[A-Za-z0-9 _.\-]{2,40}$")


def _match(row, term: str | None) -> bool:
    """Exact cell match (case-insensitive): 'BOS' matches a BOS cell, not 'BOSTON' or 'ABOS'."""
    return term is None or any(isinstance(c, str) and c.strip().upper() == term for c in row) or \
        any(not isinstance(c, str) and str(c) == term for c in row)
MAX_XLSX_BYTES = 40_000_000
DATA_EXT = (".csv", ".txt", ".xlsx", ".xls.html", ".html", ".xml", ".json")


class EvidenceFileError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class RawFiles:
    def __init__(self, raw_root: Path):
        self.root = Path(raw_root).resolve()

    def vintage_dir(self, source_id: str, period: str, vintage_id: str) -> Path:
        for part in (source_id, period, vintage_id):
            if not ID.match(part or "") or ".." in part:
                raise EvidenceFileError(400, "invalid identifier")
        d = (self.root / source_id / period / vintage_id).resolve()
        if not d.is_relative_to(self.root) or not (d / "meta.json").is_file():
            raise EvidenceFileError(404, "no such source version in the local archive")
        return d

    def meta(self, source_id: str, period: str, vintage_id: str) -> dict[str, Any]:
        return json.loads((self.vintage_dir(source_id, period, vintage_id) / "meta.json").read_text())

    def file(self, source_id: str, period: str, vintage_id: str, name: str) -> Path:
        d = self.vintage_dir(source_id, period, vintage_id)
        listed = {f["name"] for f in json.loads((d / "meta.json").read_text()).get("files", [])}
        if name not in listed or "/" in name or "\\" in name or name.startswith("."):
            raise EvidenceFileError(404, "file is not part of this source version")
        p = d / name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(self.root):
            raise EvidenceFileError(404, "file not available")
        return p

    # ------------------------------------------------------------------ previews (bounded)
    def preview(self, p: Path, member: str | None = None, sheet: str | None = None, page: int = 0,
                find: str | None = None) -> dict[str, Any]:
        page = max(0, min(int(page or 0), MAX_PAGE))
        if find is not None and not FIND.match(find):
            raise EvidenceFileError(400, "find must be a short code or word")
        self._find = find.strip().upper() if find else None
        name = p.name.lower()
        out: dict[str, Any] = {"file": p.name, "bytes": p.stat().st_size}
        if name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                infos = [i for i in z.infolist() if not i.is_dir()]
                out["members"] = [{"name": i.filename, "bytes": i.file_size} for i in infos]
                data = [i for i in infos if i.filename.lower().endswith(DATA_EXT)]
                pick = next((i for i in infos if i.filename == member), None) if member else \
                    (max(data, key=lambda i: i.file_size) if data else None)
                if member and pick is None:
                    raise EvidenceFileError(404, "no such member in this archive")
                if pick is None:
                    out["note"] = "No previewable table in this archive; download it to open."
                    return out
                out["member"] = pick.filename
                with z.open(pick) as fh:
                    out.update(self._table(pick.filename.lower(), fh, pick.file_size, sheet, page))
            return out
        with open(p, "rb") as fh:
            out.update(self._table(name, fh, out["bytes"], sheet, page))
        return out

    def _table(self, name: str, fh, size: int, sheet: str | None, page: int) -> dict[str, Any]:
        if name.endswith((".csv", ".txt")):
            return _csv_page(fh, page, self._find)
        if name.endswith(".xlsx"):
            if size > MAX_XLSX_BYTES:
                return {"note": "Workbook too large to preview here; download it to open."}
            return _xlsx_page(io.BytesIO(fh.read(MAX_XLSX_BYTES + 1)), sheet, page, self._find)
        if name.endswith((".html", ".xls.html")):
            return _html_table_page(fh.read(5_000_000).decode("utf-8", "replace"), page, self._find)
        if name.endswith((".xml", ".json")):
            return {"text": fh.read(20_000).decode("utf-8", "replace"), "truncated": size > 20_000}
        return {"note": "This file type is not previewed (for example PDF); download it to open."}


def _is_header(row) -> bool:
    """Report-style files (FAA workbooks, ATADS HTML) start with title lines; the column header is the first row with
    at least three filled cells."""
    return sum(1 for c in row if c not in (None, "") and str(c).strip()) >= 3


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat()[:19]
    s = v if isinstance(v, (int, float)) else str(v)
    return s[:MAX_CELL] if isinstance(s, str) else s


def _csv_page(fh, page: int, find: str | None = None) -> dict[str, Any]:
    text = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace", newline="")
    r = csv.reader(text)
    header = next(r, [])
    rows, start, hit, scanned = [], page * PAGE_ROWS, 0, 0
    for row in r:
        scanned += 1
        if scanned > MAX_SCAN_ROWS:
            break
        if not _match(row, find):
            continue
        hit += 1
        if hit <= start:
            continue
        if len(rows) >= PAGE_ROWS:
            return {"columns": [_cell(c) for c in header[:MAX_COLS]], "rows": rows, "page": page, "more": True,
                    "first_row": start + 1, "find": find}
        rows.append([_cell(c) for c in row[:MAX_COLS]])
    return {"columns": [_cell(c) for c in header[:MAX_COLS]], "rows": rows, "page": page, "more": False,
            "first_row": start + 1, "find": find, "scan_limited": scanned > MAX_SCAN_ROWS}


def _xlsx_page(buf, sheet: str | None, page: int, find: str | None = None) -> dict[str, Any]:
    import openpyxl
    wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
    try:
        names = wb.sheetnames
        ws = wb[sheet] if sheet in names else wb[names[0]]
        start, rows, header, titles = page * PAGE_ROWS, [], None, []
        more, hit = False, 0
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if header is None:
                if _is_header(row) or i >= 10:
                    header = [_cell(c) for c in row[:MAX_COLS]]
                elif any(c not in (None, "") for c in row):
                    titles.append(" ".join(str(c) for c in row if c not in (None, ""))[:200])
                continue
            if not _match(row, find):
                continue
            hit += 1
            if hit <= start:
                continue
            if len(rows) >= PAGE_ROWS:
                more = True
                break
            rows.append([_cell(c) for c in row[:MAX_COLS]])
        return {"sheets": names, "sheet": ws.title, "columns": header or [], "rows": rows, "page": page, "more": more,
                "first_row": start + 1, "find": find, "titles": titles}
    finally:
        wb.close()


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.in_cell = [], None, [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.in_cell, self.cell = True, []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.in_cell = False
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)


def _html_table_page(html: str, page: int, find: str | None = None) -> dict[str, Any]:
    t = _Tables()
    t.feed(html)
    if not t.rows:
        return {"note": "No table found in this file."}
    k = next((i for i, r in enumerate(t.rows[:10]) if _is_header(r)), 0)
    titles = [" ".join(c for c in r if c)[:200] for r in t.rows[:k]]
    header, body = t.rows[k], [r for r in t.rows[k + 1:] if _match(r, find)]
    start = page * PAGE_ROWS
    return {"columns": [_cell(c) for c in header[:MAX_COLS]],
            "rows": [[_cell(c) for c in r[:MAX_COLS]] for r in body[start:start + PAGE_ROWS]],
            "page": page, "more": len(body) > start + PAGE_ROWS, "first_row": start + 1, "find": find, "titles": titles}
