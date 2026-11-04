"""Conversation memory & context management.

Layers (see docs/08-memory-and-context.md):
  1. Transcript      — every message of every turn, append-only (SQLite). Never summarised away, never rewritten.
  2. Evidence        — findings F# with full provenance, persisted per conversation; ids are stable forever.
                       The ONLY source of numbers. Summaries and state may *reference* F#, never restate values.
  3. State           — structured, deterministic: entities (by recency), metrics, windows, assumptions (versioned,
                       superseded on correction), decisions, answers (headline + cited F#). Updated from tool calls
                       and from validated `update_memory` calls.
  4. Rolling summary — narrative compaction of turns that fell out of the recent window. Validated: no numerals
                       except F#/A# references and years. If the summariser violates this, an extractive fallback is used.
  5. Context builder — token-budgeted assembly per request: memory block (state + findings index + summary +
                       retrieved older turns) + recent turns verbatim, with old tool results collapsed to F# pointers.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from airport_analytics.evidence import EvidenceStore, Finding, SourceRef

FID = re.compile(r"\bF\d+\b")


def est_tokens(x: Any) -> int:
    """Cheap, provider-neutral token estimate (≈4 chars/token); used only for budgeting."""
    return max(1, len(x if isinstance(x, str) else json.dumps(x, default=str)) // 4)


# ------------------------------------------------------------------ persistence
SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS messages (conv_id TEXT, seq INTEGER, turn INTEGER, role TEXT, content TEXT, tokens INTEGER,
                                     created_at REAL, PRIMARY KEY (conv_id, seq));
CREATE TABLE IF NOT EXISTS findings (conv_id TEXT, fid TEXT, n INTEGER, body TEXT, PRIMARY KEY (conv_id, fid));
CREATE TABLE IF NOT EXISTS state (conv_id TEXT PRIMARY KEY, body TEXT);
CREATE TABLE IF NOT EXISTS state_log (conv_id TEXT, turn INTEGER, change TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS summaries (conv_id TEXT, upto_turn INTEGER, method TEXT, body TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS traces (conv_id TEXT, turn INTEGER, body TEXT, created_at REAL);
"""


class ConversationStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    # conversations
    def create(self, conv_id: str, title: str = "") -> None:
        now = time.time()
        self.db.execute("INSERT OR IGNORE INTO conversations VALUES (?,?,?,?)", (conv_id, title, now, now))
        self.db.commit()

    def list(self) -> list[dict]:
        rows = self.db.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC").fetchall()
        return [dict(zip(("id", "title", "created_at", "updated_at"), r)) for r in rows]

    def set_title(self, conv_id: str, title: str) -> None:
        self.db.execute("UPDATE conversations SET title = ? WHERE id = ? AND (title IS NULL OR title = '')", (title, conv_id))
        self.db.commit()

    def touch(self, conv_id: str) -> None:
        self.db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (time.time(), conv_id))
        self.db.commit()

    # transcript
    def append(self, conv_id: str, turn: int, role: str, content: Any) -> None:
        seq = self.db.execute("SELECT coalesce(max(seq), -1) + 1 FROM messages WHERE conv_id = ?", (conv_id,)).fetchone()[0]
        body = json.dumps(content, default=str)
        self.db.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?)", (conv_id, seq, turn, role, body, est_tokens(body), time.time()))
        self.db.commit()

    def messages(self, conv_id: str) -> list[dict]:
        rows = self.db.execute("SELECT seq, turn, role, content, tokens FROM messages WHERE conv_id = ? ORDER BY seq", (conv_id,)).fetchall()
        return [{"seq": s, "turn": t, "role": r, "content": json.loads(c), "tokens": k} for s, t, r, c, k in rows]

    def last_turn(self, conv_id: str) -> int:
        return self.db.execute("SELECT coalesce(max(turn), 0) FROM messages WHERE conv_id = ?", (conv_id,)).fetchone()[0]

    # evidence
    def save_findings(self, conv_id: str, store: EvidenceStore) -> None:
        for f in store.all():
            self.db.execute("INSERT OR IGNORE INTO findings VALUES (?,?,?,?)",
                            (conv_id, f.id, int(f.id[1:]), json.dumps(f.to_dict(), default=str)))
        self.db.commit()

    def load_findings(self, conv_id: str) -> EvidenceStore:
        st = EvidenceStore()
        for (body,) in self.db.execute("SELECT body FROM findings WHERE conv_id = ? ORDER BY n", (conv_id,)).fetchall():
            d = json.loads(body)
            d["sources"] = [SourceRef(**s) for s in d.get("sources", [])]
            st.add(Finding(**d))
        st._n = max((int(f.id[1:]) for f in st.all()), default=0)      # ids continue, never reused
        return st

    # state & summaries & traces
    def load_state(self, conv_id: str) -> "ConversationState":
        r = self.db.execute("SELECT body FROM state WHERE conv_id = ?", (conv_id,)).fetchone()
        return ConversationState.from_dict(json.loads(r[0])) if r else ConversationState()

    def save_state(self, conv_id: str, s: "ConversationState", turn: int, changes: list[dict]) -> None:
        self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (conv_id, json.dumps(asdict(s))))
        for c in changes:
            self.db.execute("INSERT INTO state_log VALUES (?,?,?,?)", (conv_id, turn, json.dumps(c), time.time()))
        self.db.commit()

    def latest_summary(self, conv_id: str) -> dict | None:
        r = self.db.execute("SELECT upto_turn, method, body FROM summaries WHERE conv_id = ? ORDER BY upto_turn DESC LIMIT 1",
                            (conv_id,)).fetchone()
        return {"upto_turn": r[0], "method": r[1], "text": r[2]} if r else None

    def save_summary(self, conv_id: str, upto_turn: int, method: str, text: str) -> None:
        self.db.execute("INSERT INTO summaries VALUES (?,?,?,?,?)", (conv_id, upto_turn, method, text, time.time()))
        self.db.commit()

    def save_trace(self, conv_id: str, turn: int, trace: dict) -> None:
        self.db.execute("INSERT INTO traces VALUES (?,?,?,?)", (conv_id, turn, json.dumps(trace, default=str), time.time()))
        self.db.commit()

    def traces(self, conv_id: str) -> list[dict]:
        return [json.loads(b) for (b,) in self.db.execute("SELECT body FROM traces WHERE conv_id = ? ORDER BY turn", (conv_id,))]


# ------------------------------------------------------------------ structured state
@dataclass
class ConversationState:
    entities: dict[str, dict] = field(default_factory=dict)     # code/group key -> {kind, label, ids, first, last, n}
    metrics: dict[str, int] = field(default_factory=dict)       # metric id -> last turn used
    windows: list[dict] = field(default_factory=list)           # [{spec, turn}]
    assumptions: list[dict] = field(default_factory=list)       # [{id: A#, text, status, turn, superseded_by}]
    decisions: list[dict] = field(default_factory=list)         # [{text, turn, support: [F#]}]
    answers: list[dict] = field(default_factory=list)           # [{turn, question, headline, cited: [F#]}]
    preferences: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict) -> "ConversationState":
        return ConversationState(**{k: d.get(k, v) for k, v in asdict(ConversationState()).items()})

    # -------- deterministic updates from tool calls
    def observe(self, tool: str, args: dict, result: Any, turn: int, resolver=None) -> list[dict]:
        ch: list[dict] = []

        def touch(key, kind, label, ids=None):
            e = self.entities.get(key)
            if e:
                e["last"], e["n"] = turn, e["n"] + 1
            else:
                self.entities[key] = {"kind": kind, "label": label, "ids": ids or [], "first": turn, "last": turn, "n": 1}
                ch.append({"op": "entity_added", "key": key, "turn": turn})
        if tool == "resolve_entities" and isinstance(result, dict):
            for r in result.get("resolutions", []):
                if r.get("kind") == "airport":
                    ids = r.get("airport_ids") or []
                    c = next((c for c in r.get("candidates", []) if c.get("code") and c.get("airport_id") in ids), None)
                    if c:
                        touch(c["code"], "airport", c.get("name") or r["term"], ids)
                elif r.get("kind") == "group":
                    touch(r["term"], "group", r.get("note") or r["term"], r.get("airport_ids"))
        if tool == "run_analysis" and isinstance(result, dict) and not result.get("error"):
            spec = args.get("spec") or args
            ent = result.get("entities") or {}
            for a in ent.get("airports", []) or []:
                touch(a["code"], "airport", a.get("name") or a["code"], [a["airport_id"]])
            if ent.get("group"):
                key = json.dumps(ent["group"], sort_keys=True)
                touch(key, "group", ", ".join(f"{k}={v}" for k, v in ent["group"].items()))
            for m in spec.get("metrics") or []:
                mid = m if isinstance(m, str) else m.get("id")
                if mid:
                    self.metrics[mid] = turn
            for c in (spec.get("options") or {}).get("criteria") or []:
                mid = c["metric"] if isinstance(c.get("metric"), str) else (c.get("metric") or {}).get("id")
                if mid:
                    self.metrics[mid] = turn
            if spec.get("op") == "screen":
                self.metrics["screen_score"] = turn
            if spec.get("window"):
                self.windows.append({"spec": spec["window"], "turn": turn})
                self.windows = self.windows[-8:]
        return ch

    # -------- validated model-initiated updates
    def apply_update(self, upd: dict, turn: int) -> tuple[dict | None, str | None]:
        action, text = upd.get("action"), (upd.get("text") or "").strip()
        if action not in ("set_assumption", "retract_assumption", "note_decision", "set_preference"):
            return None, "action must be set_assumption|retract_assumption|note_decision|set_preference"
        if action == "retract_assumption":
            a = next((x for x in self.assumptions if x["id"] == upd.get("id")), None)
            if not a:
                return None, f"unknown assumption id {upd.get('id')}"
            a["status"] = "retracted"
            return {"op": "assumption_retracted", "id": a["id"], "turn": turn}, None
        if not text or len(text) > 400:
            return None, "text required (≤400 chars)"
        if action == "set_assumption":
            new = {"id": f"A{len(self.assumptions) + 1}", "text": text, "status": "active", "turn": turn, "superseded_by": None}
            rep = upd.get("replaces")
            if rep:
                old = next((x for x in self.assumptions if x["id"] == rep), None)
                if not old:
                    return None, f"unknown assumption id {rep}"
                old["status"], old["superseded_by"] = "superseded", new["id"]
            self.assumptions.append(new)
            return {"op": "assumption_set", **new}, None
        if action == "note_decision":
            sup = [s for s in upd.get("support") or [] if FID.fullmatch(s)]
            if re.search(r"\d", FID.sub("", text)):
                return None, "decisions may reference findings (F#) but must not restate numbers"
            d = {"text": text, "turn": turn, "support": sup}
            self.decisions.append(d)
            return {"op": "decision_noted", **d}, None
        key = upd.get("key") or ""
        if not key:
            return None, "set_preference needs key"
        self.preferences[key] = text
        return {"op": "preference_set", "key": key, "value": text, "turn": turn}, None

    def focus(self, n: int = 6) -> list[tuple[str, dict]]:
        return sorted(self.entities.items(), key=lambda kv: (-kv[1]["last"], -kv[1]["n"]))[:n]


# ------------------------------------------------------------------ summaries (no numbers, references only)
NUM_OUTSIDE_REFS = re.compile(r"\d")


def summary_is_safe(text: str) -> bool:
    """A summary may mention F#/A# ids, turn numbers and years; any other digit makes it a would-be source of numbers -> reject."""
    t = re.sub(r"\b[FA]\d+\b|\b[Tt]urns? \d+(?:\s*(?:-|–|and|to)\s*\d+)?\b", "", text)
    t = re.sub(r"\b(19|20)\d\d\b|\b(FY|CY)\s?\d{2,4}\b|\bT-100\b|\bT12\b", "", t)
    return not NUM_OUTSIDE_REFS.search(t)


def extractive_summary(turn_records: list[dict]) -> str:
    """Deterministic fallback: one line per turn — the user's question (digits stripped) and the answer headline refs."""
    lines = []
    for r in turn_records:
        q = re.sub(r"\d[\d,.%]*", "#", r.get("question", ""))[:160]
        cited = ", ".join(r.get("cited", [])[:8])
        lines.append(f"- Turn {r['turn']}: user asked \"{q}\"" + (f"; answered with {cited}" if cited else "; no grounded answer"))
    return "\n".join(lines)


SUMMARY_PROMPT = ("Summarise the conversation turns below for an analyst assistant's memory. Keep: what the user wanted, "
                  "entities and metrics discussed, assumptions and decisions, unresolved questions. Refer to results ONLY "
                  "by finding id (e.g. 'see F12'); DO NOT write any numbers, percentages, amounts or counts. Max 12 bullets.")


def summarize(turn_records: list[dict], summarizer: Callable[[str], str] | None) -> tuple[str, str]:
    """Return (text, method). A model summary is accepted only if it is number-free; otherwise extractive."""
    if summarizer:
        src = "\n".join(f"Turn {r['turn']} USER: {r.get('question', '')}\nASSISTANT: {r.get('headline', '')} "
                        f"[cited: {', '.join(r.get('cited', []))}]" for r in turn_records)
        try:
            txt = summarizer(SUMMARY_PROMPT + "\n\n" + src)
            if txt and summary_is_safe(txt):
                return txt.strip(), "model"
        except Exception:
            pass
    return extractive_summary(turn_records), "extractive"


# ------------------------------------------------------------------ retrieval over older turns (lexical, no vector DB)
_TOK = re.compile(r"[A-Za-z][A-Za-z0-9_]+|F\d+")
STOP = set("the a an of in on for to and or is are was were what which how did does do vs with at by from it its this that "
           "be as me my we our you your can could would should please show tell about".split())


def _toks(t: str) -> list[str]:
    return [w.lower() if not re.fullmatch(r"[A-Z0-9]{3,4}|F\d+", w) else w for w in _TOK.findall(t or "") if w.lower() not in STOP]


def retrieve(query: str, docs: list[tuple[str, str]], k: int = 3) -> list[tuple[str, float]]:
    """BM25 over (doc_id, text). Airport codes and finding ids are kept case-sensitive tokens (exact matches)."""
    q = _toks(query)
    if not q or not docs:
        return []
    toks = [_toks(t) for _, t in docs]
    N, avg = len(docs), sum(map(len, toks)) / max(1, len(docs))
    df = Counter(w for ts in toks for w in set(ts))
    out = []
    for (did, _), ts in zip(docs, toks):
        tf = Counter(ts)
        s = sum(math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(ts) / avg))
                for w in q if w in tf)
        if s > 0:
            out.append((did, s))
    return sorted(out, key=lambda x: -x[1])[:k]


# ------------------------------------------------------------------ context builder
@dataclass
class Budget:
    total: int = 24_000          # tokens for messages + memory block (system prompt and tool schemas are separate)
    recent_share: float = 0.55
    findings_share: float = 0.15
    state_share: float = 0.08
    summary_share: float = 0.10
    retrieval_share: float = 0.12


def compact_old_tool_results(msgs: list[dict]) -> list[dict]:
    """Replace bodies of tool results from PREVIOUS turns with a pointer to the stored findings."""
    out = []
    for m in msgs:
        c = m["content"]
        if m["role"] == "user" and isinstance(c, list) and any(b.get("type") == "tool_result" for b in c):
            nb = []
            for b in c:
                if b.get("type") == "tool_result":
                    ids = sorted(set(FID.findall(b.get("content", ""))), key=lambda x: int(x[1:]))
                    ptr = (f"[earlier tool result; findings {ids[0]}…{ids[-1]} ({len(ids)}) are stored — use get_finding/recall]"
                           if ids else "[earlier tool result omitted — re-run or use recall if needed]")
                    nb.append({**b, "content": ptr})
                else:
                    nb.append(b)
            out.append({**m, "content": nb})
        else:
            out.append(m)
    return out


class ContextBuilder:
    def __init__(self, store: ConversationStore, budget: Budget | None = None):
        self.store, self.budget = store, budget or Budget()

    def findings_index(self, ev: EvidenceStore, state: ConversationState, query: str, limit_tokens: int, fmt,
                       boost: set[str] | None = None) -> list[str]:
        """Authoritative findings (values read from the store, not from memory), most relevant first."""
        cited = [fid for a in reversed(state.answers) for fid in a.get("cited", [])]
        focus_codes = {k for k, e in state.focus(8) if e["kind"] == "airport"}
        qtok = set(_toks(query))
        scored = []
        for f in ev.all():
            if f.epistemic_class == "exploratory":
                continue
            s = (10 if f.id in qtok else 0) + (4 if boost and f.id in boost else 0) + (3 if f.id in cited else 0) \
                + (2 if f.subject.get("airport_code") in focus_codes else 0) + len(qtok & set(_toks(f.label))) \
                + int(f.id[1:]) / 1e6
            scored.append((s, f))
        lines, used = [], 0
        for _, f in sorted(scored, key=lambda x: -x[0]):
            line = f"{f.id}: {f.label} = {fmt(f)} [{f.epistemic_class}]"
            t = est_tokens(line)
            if used + t > limit_tokens:
                break
            lines.append(line)
            used += t
        return lines

    def build(self, conv_id: str, question: str, state: ConversationState, ev: EvidenceStore, fmt) -> tuple[str, list[dict], dict]:
        """-> (memory_block, messages for the model, stats)."""
        B = self.budget
        msgs = self.store.messages(conv_id)
        # recent turns verbatim (newest first until budget), older tool results compacted to pointers
        turns = sorted({m["turn"] for m in msgs})
        recent, used, kept_turns = [], 0, []
        for t in reversed(turns):
            block = [{"role": m["role"], "content": m["content"]} for m in msgs if m["turn"] == t]
            block = compact_old_tool_results(block)
            cost = est_tokens(block)
            if kept_turns and used + cost > B.total * B.recent_share:
                break
            recent = block + recent
            used += cost
            kept_turns.append(t)
        older = [t for t in turns if t not in kept_turns]
        # memory block
        parts = []
        st_lines = []
        if state.entities:
            st_lines.append("Entities in focus (most recent first): " + "; ".join(
                f"{k} ({e['kind']}, first turn {e['first']}, last turn {e['last']})" for k, e in state.focus(10)))
        if state.metrics:
            st_lines.append("Metrics used: " + ", ".join(sorted(state.metrics, key=lambda m: -state.metrics[m])[:12]))
        act = [a for a in state.assumptions if a["status"] == "active"]
        sup = [a for a in state.assumptions if a["status"] != "active"]
        if act:
            st_lines.append("Active assumptions: " + "; ".join(f"{a['id']}: {a['text']}" for a in act))
        if sup:
            st_lines.append("No longer valid (do not use): " + "; ".join(f"{a['id']} ({a['status']}): {a['text']}" for a in sup[-6:]))
        if state.decisions:
            st_lines.append("Decisions: " + "; ".join(f"{d['text']} [{', '.join(d['support'])}]" for d in state.decisions[-6:]))
        if state.preferences:
            st_lines.append("Preferences: " + "; ".join(f"{k}={v}" for k, v in state.preferences.items()))
        st_txt = "\n".join(st_lines)[: int(B.total * B.state_share) * 4]
        if st_txt:
            parts.append("## Conversation state\n" + st_txt)
        older_docs = []
        for t in older:
            q = next((m["content"] for m in msgs if m["turn"] == t and m["role"] == "user" and isinstance(m["content"], str)), "")
            a = next((x for x in state.answers if x["turn"] == t), {})
            older_docs.append((str(t), f"{q} {a.get('headline', '')} {' '.join(a.get('cited', []))}"))
        hits = retrieve(question, older_docs, k=4) if older else []
        boost = {fid for did, _ in hits for x in state.answers if str(x["turn"]) == did for fid in x.get("cited", [])}
        fi = self.findings_index(ev, state, question, int(B.total * B.findings_share), fmt, boost)
        if fi:
            parts.append("## Findings available (authoritative values; cite by id, e.g. {F3})\n" + "\n".join(fi))
        summ = self.store.latest_summary(conv_id)
        if summ and older:
            parts.append(f"## Summary of earlier turns (≤{summ['upto_turn']}, {summ['method']}; contains no numbers — use findings)\n"
                         + summ["text"][: int(B.total * B.summary_share) * 4])
        if older:
            rl, used_r = [], 0
            for did, _ in hits:
                a = next((x for x in state.answers if x["turn"] == int(did)), {})
                q = next((m["content"] for m in msgs if m["turn"] == int(did) and m["role"] == "user" and isinstance(m["content"], str)), "")
                line = f"- Turn {did}: \"{q[:200]}\" → {a.get('headline', '(no answer)')} [cited {', '.join(a.get('cited', [])) or 'none'}]"
                if used_r + est_tokens(line) > B.total * B.retrieval_share:
                    break
                rl.append(line)
                used_r += est_tokens(line)
            if rl:
                parts.append("## Possibly relevant earlier turns (retrieved)\n" + "\n".join(rl))
        mem = "\n\n".join(parts)
        stats = {"turns_total": len(turns), "turns_verbatim": len(kept_turns), "turns_summarised": len(older),
                 "recent_tokens": used, "memory_tokens": est_tokens(mem) if mem else 0,
                 "findings_listed": len(fi), "findings_total": len(ev.all())}
        return mem, recent, stats

    def maybe_compact(self, conv_id: str, state: ConversationState, summarizer=None, trigger_turns: int = 6) -> dict | None:
        """Roll the summary forward when ≥ trigger_turns turns are not covered by it and fall outside the recent window."""
        msgs = self.store.messages(conv_id)
        turns = sorted({m["turn"] for m in msgs})
        if not turns:
            return None
        recent_tokens, keep = 0, []
        for t in reversed(turns):
            c = est_tokens([m["content"] for m in msgs if m["turn"] == t])
            if keep and recent_tokens + c > self.budget.total * self.budget.recent_share:
                break
            keep.append(t)
            recent_tokens += c
        older = [t for t in turns if t not in keep]
        prev = self.store.latest_summary(conv_id)
        covered = prev["upto_turn"] if prev else 0
        pending = [t for t in older if t > covered]
        if len(pending) < trigger_turns and not (older and len(older) - covered >= trigger_turns):
            return None
        upto = max(older)
        recs = []
        for t in older:
            q = next((m["content"] for m in msgs if m["turn"] == t and m["role"] == "user" and isinstance(m["content"], str)), "")
            a = next((x for x in state.answers if x["turn"] == t), {})
            recs.append({"turn": t, "question": q, "headline": a.get("headline", ""), "cited": a.get("cited", [])})
        text, method = summarize(recs, summarizer)
        self.store.save_summary(conv_id, upto, method, text)
        return {"upto_turn": upto, "method": method}
