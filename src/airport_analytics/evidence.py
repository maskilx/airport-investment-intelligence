"""Evidence model: every number the engine produces is a Finding with full lineage.

Typed errors become `not_established` outcomes the agent must relay; nothing is silently filled.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

EPISTEMIC = ("observed", "calculated", "forecast", "estimated", "hypothesis", "exploratory", "not_established")


class AnalyticsError(Exception):
    code = "analytics_error"

    def __init__(self, message: str, **detail: Any):
        super().__init__(message)
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": str(self), **self.detail}


class OutOfCoverage(AnalyticsError):
    code = "out_of_coverage"


class AmbiguousEntity(AnalyticsError):
    code = "ambiguous_entity"


class UnknownEntity(AnalyticsError):
    code = "unknown_entity"


class InvalidSpec(AnalyticsError):
    code = "invalid_spec"


class NotApplicable(AnalyticsError):
    code = "not_applicable"


class InsufficientData(AnalyticsError):
    code = "insufficient_data"


@dataclass
class SourceRef:
    source_id: str
    periods: list[str]
    vintage_ids: list[str]

    def label(self) -> str:
        p = self.periods
        span = p[0] if len(p) == 1 else (f"{p[0]}…{p[-1]} ({len(p)} periods)" if p else "n/a")
        return f"{self.source_id} [{span}]"


@dataclass
class Finding:
    id: str
    metric_id: str
    label: str                       # human label, e.g. "Seat factor — SFO, 2025-08…2026-07"
    value: float | int | str | None
    unit: str
    fmt: str
    epistemic_class: str
    definition: str
    formula_version: str
    subject: dict[str, Any]          # {airport_id, code} or {group: ...} plus any breakdown keys
    window: dict[str, Any]
    sources: list[SourceRef]
    caveats: list[str] = field(default_factory=list)
    coverage: dict[str, Any] | None = None
    inputs: list[str] = field(default_factory=list)     # finding ids this one derives from
    spec: dict[str, Any] | None = None                  # reproducing analysis spec (partial; see execution)
    catalog_version: str = ""
    # Execution envelope: everything needed to replay the ORIGINAL operation (tool, op, full spec, resolved entity
    # ids, scenario, config hash, data build fingerprint). Set by the tool layer, never by the model.
    execution: dict[str, Any] | None = None
    # Assumption dependencies (A# ids active when this finding was produced, plus structured parameter bindings).
    assumptions: list[str] = field(default_factory=list)
    # current | stale. A stale finding may be inspected but never cited (render.validate enforces it).
    status: str = "current"
    status_reason: str = ""

    def brief(self) -> dict[str, Any]:
        """Compact form returned to the model."""
        d = {"id": self.id, "label": self.label, "value": self.value, "unit": self.unit, "class": self.epistemic_class}
        if self.coverage:
            d["coverage"] = self.coverage
        if self.caveats:
            d["caveats"] = self.caveats
        if self.status != "current":
            d["status"], d["status_reason"] = self.status, self.status_reason
        return d

    def result_key(self) -> str:
        """Identity of this result within its operation's output (used to find the counterpart on replay)."""
        subj = {k: v for k, v in self.subject.items() if k != "rank"}
        return f"{self.metric_id}|{json.dumps(subj, sort_keys=True, default=str)}|{self.window.get('label', '')}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class EvidenceStore:
    """Session-scoped registry of findings (ids are stable within a session)."""

    def __init__(self):
        self._items: dict[str, Finding] = {}
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"F{self._n}"

    def add(self, f: Finding) -> Finding:
        self._items[f.id] = f
        return f

    def get(self, fid: str) -> Finding:
        if fid not in self._items:
            raise UnknownEntity(f"unknown finding id {fid}")
        return self._items[fid]

    def __contains__(self, fid: str) -> bool:
        return fid in self._items

    def all(self) -> list[Finding]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def added_since(self, n: int) -> list[Finding]:
        """Findings registered after the store held `n` items (insertion order)."""
        return list(self._items.values())[n:]

    def current(self) -> list[Finding]:
        return [f for f in self._items.values() if f.status == "current"]


def spec_hash(spec: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:12]


def file_hash(path) -> str:
    from pathlib import Path
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
