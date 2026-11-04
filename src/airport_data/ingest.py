"""Fetch orchestration: download -> integrity check -> raw store (or event on failure)."""
from __future__ import annotations

from dataclasses import dataclass

from .events import EventLog
from .http import HttpClient
from .rawstore import RawStore
from .sources.base import Source


@dataclass
class FetchOutcome:
    source_id: str
    period: str
    action: str            # stored | unchanged | failed | rejected
    vintage_id: str | None = None
    detail: str = ""


def fetch_period(src: Source, period: str, store: RawStore, log: EventLog, http: HttpClient) -> FetchOutcome:
    try:
        res = src.fetch(period, http)
    except Exception as e:  # network/format failure: nothing stored, previous vintage keeps serving
        log.write(src.id, period, "failed", error=f"{type(e).__name__}: {e}")
        return FetchOutcome(src.id, period, "failed", detail=str(e))

    problems = src.integrity_errors(res.files)
    if problems:
        log.write(src.id, period, "rejected", errors=problems, url=res.url)
        return FetchOutcome(src.id, period, "rejected", detail="; ".join(problems))

    meta = {"url": res.url, "request": res.request, "response_headers": res.response_headers,
            "source_reported": res.source_reported, "source_title": src.title, "license": src.license}
    v, created = store.put(src.id, period, res.files, meta)
    action = "stored" if created else "unchanged"
    log.write(src.id, period, action, vintage_id=v.vintage_id, content_sha256=v.content_sha256,
              bytes=sum(f["bytes"] for f in v.files))
    return FetchOutcome(src.id, period, action, v.vintage_id)


def resolve_periods(src: Source, spec: str, http: HttpClient) -> list[str]:
    """spec: 'latest' | 'available' | 'YYYY-MM:YYYY-MM' | comma list of periods."""
    from .sources.base import month_periods
    if spec in ("latest", "available"):
        avail = src.available_periods(http)
        return avail[-1:] if spec == "latest" else avail
    if ":" in spec:
        a, b = spec.split(":")
        if src.period_kind == "month":
            return month_periods(a, b)
        return [str(y) for y in range(int(a), int(b) + 1)]
    return [p.strip() for p in spec.split(",") if p.strip()]
