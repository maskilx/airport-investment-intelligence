"""Live airport status from the FAA NAS Status API (public REST API, no key): https://nasstatus.faa.gov/api/airport-status-information

Current ground delay programs, ground stops, arrival/departure delays and closures. This is LIVE context, not part of
the reproducible database: each response is stored as external evidence (W#, with retrieval time and sha256) and can
only be cited through an external claim with a verbatim quote of the stored text, exactly like web research.
The URL is a fixed constant (no user input reaches it); the response is parsed as XML with no external entities.
"""
from __future__ import annotations

import hashlib
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Callable

NAS_STATUS_URL = "https://nasstatus.faa.gov/api/airport-status-information"


def parse(xml_text: str) -> tuple[str, list[dict]]:
    if "<!DOCTYPE" in xml_text.upper() and "ENTITY" in xml_text.upper():
        raise ValueError("refusing XML with entity declarations")
    root = ET.fromstring(xml_text)
    updated = (root.findtext("Update_Time") or "").strip()
    out = []
    for dt in root.findall("Delay_type"):
        kind = (dt.findtext("Name") or "").strip()
        for el in dt.iter():
            arpt = el.findtext("ARPT")
            if not arpt or el.tag in ("Delay_type",):
                continue
            d = {"airport": arpt.strip().upper(), "program": kind, "reason": (el.findtext("Reason") or "").strip()}
            for tag in ("Avg", "Max", "Trend", "End_Time", "Start", "Reopen"):
                if el.findtext(tag):
                    d[tag.lower()] = el.findtext(tag).strip()
            arr = el.find("Arrival_Departure")
            if arr is not None:
                d["direction"] = arr.get("Type", "")
                for tag in ("Min", "Max", "Trend"):
                    if arr.findtext(tag):
                        d[tag.lower()] = arr.findtext(tag).strip()
            out.append(d)
    return updated, out


def render_lines(updated: str, items: list[dict], airports: list[str]) -> list[str]:
    lines = [f"FAA NAS Status, updated {updated}."]
    want = [a.upper() for a in airports] or sorted({i["airport"] for i in items})
    for a in want:
        hits = [i for i in items if i["airport"] == a]
        if not hits:
            lines.append(f"{a}: no ground delay program, ground stop, delay or closure is listed.")
        for i in hits:
            parts = [f"{a}: {i['program']}"] + [f"{k} {str(v).rstrip('.')}" for k, v in i.items()
                                                 if k not in ("airport", "program") and v]
            lines.append(", ".join(parts) + ".")
    return lines


class LiveStatus:
    """Tool provider: live_airport_status -> W# external evidence in the conversation's external store."""

    def __init__(self, items: dict[str, dict], fetch: Callable[[], str] | None = None, timeout: float = 10.0):
        self.items, self.timeout = items, timeout
        self._fetch = fetch or self._http

    def _http(self) -> str:
        import ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        req = urllib.request.Request(NAS_STATUS_URL, headers={"User-Agent": "airport-intel", "Accept": "application/xml"})
        with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as r:
            return r.read(2_000_000).decode("utf-8", "replace")

    def call(self, a: dict) -> dict[str, Any]:
        airports = [str(x).upper()[:4] for x in (a.get("airports") or [])][:10]
        updated, items = parse(self._fetch())
        lines = render_lines(updated, items, airports)
        text = "\n".join(lines)
        wid = f"W{max([int(k[1:]) for k in self.items] or [0]) + 1}"
        self.items[wid] = {"id": wid, "kind": "external_api", "url": NAS_STATUS_URL, "requested_url": NAS_STATUS_URL,
                           "title": "FAA NAS Status: live airport status", "domain": "nasstatus.faa.gov",
                           "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text), "text": text}
        return {"id": wid, "source": "FAA NAS Status API (live, public)", "updated": updated, "lines": lines,
                "note": "Live operational status, not part of the reproducible dataset. Cite it only with an external "
                        f"claim: source {wid} and a verbatim quote of one of these lines."}

    def tools(self) -> dict[str, tuple[dict, Callable]]:
        schema = {"name": "live_airport_status",
                  "description": "Current FAA NAS Status for airports (live public FAA API): active ground delay "
                                 "programs, ground stops, arrival/departure delays, closures. Use only when the user "
                                 "asks about the situation now/today; historical congestion comes from run_analysis.",
                  "input_schema": {"type": "object", "properties": {"airports": {"type": "array", "items": {"type": "string"}}},
                                   "required": ["airports"]}}
        return {"live_airport_status": (schema, self.call)}
