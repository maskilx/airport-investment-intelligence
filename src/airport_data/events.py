"""Append-only log of fetch attempts (success, unchanged, failure, rejection).

Failures never touch the raw store: the previous valid vintage keeps serving,
and the failure is visible here and in the `fetch_events` DB table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .rawstore import utc_now


class EventLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def write(self, source_id: str, period: str | None, action: str, **detail: Any) -> dict[str, Any]:
        rec = {"ts": utc_now(), "source_id": source_id, "period": period, "action": action, **detail}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
