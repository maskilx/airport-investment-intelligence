"""Model-provider abstraction.

Canonical message format (Anthropic-style, provider-neutral inside the agent):
  {"role": "user" | "assistant", "content": str | [blocks]}
  blocks: {"type": "text", "text"} | {"type": "tool_use", "id", "name", "input", "provider_meta"?}
          | {"type": "tool_result", "tool_use_id", "name", "content"}
Every backend returns ModelResponse(content blocks, stop_reason, usage). Backends never execute tools.

Cost safety (Gemini free tier): GeminiBackend refuses to run unless AIRPORT_ALLOW_GEMINI=1, keeps a per-process
request budget, appends every call to a usage log, and has NO fallback to any other (paid) provider.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    requests: int = 0

    def add(self, o: "Usage") -> None:
        self.input_tokens += o.input_tokens
        self.output_tokens += o.output_tokens
        self.thinking_tokens += o.thinking_tokens
        self.requests += o.requests


@dataclass
class ModelResponse:
    content: list[dict]
    stop_reason: str                       # tool_use | end_turn | max_tokens | error
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    latency_s: float = 0.0


class ModelBackend(Protocol):
    name: str

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse: ...


class ModelError(RuntimeError):
    pass


# ------------------------------------------------------------------ scripted (tests, UI development)
class ScriptedBackend:
    """Replays assistant turns. A turn may be a list of blocks or a callable(messages) -> blocks."""
    name = "scripted"

    def __init__(self, turns: list):
        self.turns = list(turns)
        self.calls: list[dict] = []

    def complete(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages, "tools": [t["name"] for t in tools]})
        nxt = self.turns.pop(0) if self.turns else [{"type": "text", "text": "I cannot answer that."}]
        blocks = nxt(messages) if callable(nxt) else nxt
        approx = sum(len(json.dumps(m, default=str)) for m in messages) // 4
        return ModelResponse(blocks, "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn",
                             Usage(approx, sum(len(json.dumps(b)) for b in blocks) // 4, 0, 1), "scripted")


# ------------------------------------------------------------------ Gemini (REST, stdlib only)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_UNSUPPORTED_SCHEMA_KEYS = {"oneOf", "anyOf", "allOf", "$schema", "additionalProperties", "default", "examples"}


def gemini_schema(s: Any) -> Any:
    """Translate our JSON schemas to the OpenAPI subset Gemini function declarations accept."""
    if isinstance(s, dict):
        if "oneOf" in s:      # e.g. metric ref = string | object -> accept an object-or-string description
            return {"type": "string", "description": (s.get("description") or "") +
                    " (metric id, or a JSON object {id, params, window, transform} encoded as a string)"}
        out = {k: gemini_schema(v) for k, v in s.items() if k not in _UNSUPPORTED_SCHEMA_KEYS}
        if "enum" in out:
            out["type"] = "string"
            out["enum"] = [str(e) for e in out["enum"]]
        if out.get("type") == "object" and not out.get("properties"):
            # Gemini rejects OBJECT parameters without properties: free-form objects travel as JSON strings and are
            # decoded back by decode_args() before the tool runs.
            return {"type": "string", "description": (s.get("description") or "free-form options") +
                    " (a JSON object encoded as a string, e.g. {\"key\": \"value\"})"}
        if "required" in out and out.get("properties"):
            out["required"] = [r for r in out["required"] if r in out["properties"]]
        return out
    if isinstance(s, list):
        return [gemini_schema(x) for x in s]
    return s


def decode_args(v: Any) -> Any:
    """Inverse of the schema translation: JSON objects/arrays that were sent as strings become structures again."""
    if isinstance(v, dict):
        return {k: decode_args(x) for k, x in v.items()}
    if isinstance(v, list):
        return [decode_args(x) for x in v]
    if isinstance(v, str) and v[:1] in "{[" and v.strip()[-1:] in "}]":
        try:
            return decode_args(json.loads(v))
        except ValueError:
            return v
    return v


class GeminiBackend:
    """Google Gemini API generateContent with function calling. No SDK dependency; explicit, auditable requests."""
    name = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None, max_requests: int | None = None,
                 usage_log: str | Path | None = None, timeout: float = 120.0):
        if os.environ.get("AIRPORT_ALLOW_GEMINI") != "1":
            raise ModelError("Gemini calls are disabled (set AIRPORT_ALLOW_GEMINI=1 to allow real API calls)")
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ModelError("no GEMINI_API_KEY in the environment")
        self.model = model or os.environ.get("AIRPORT_GEMINI_MODEL", "gemini-3.8-flash")
        self.max_requests = int(max_requests or os.environ.get("AIRPORT_GEMINI_MAX_REQUESTS", 25))
        self.usage_log = Path(usage_log or os.environ.get("AIRPORT_GEMINI_USAGE_LOG", "data/app/gemini_usage.jsonl"))
        self.timeout = timeout
        self.requests = 0

    # canonical -> Gemini
    @staticmethod
    def to_contents(messages: list[dict]) -> list[dict]:
        names: dict[str, str] = {}
        out = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            blocks = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
            parts = []
            for b in blocks:
                if b["type"] == "text" and b.get("text"):
                    parts.append({"text": b["text"]})
                elif b["type"] == "tool_use":
                    names[b["id"]] = b["name"]
                    p = {"functionCall": {"name": b["name"], "args": b.get("input") or {}}}
                    sig = (b.get("provider_meta") or {}).get("thoughtSignature")
                    if sig:                                  # Gemini 3 requires the signature to be echoed back
                        p["thoughtSignature"] = sig
                    parts.append(p)
                elif b["type"] == "tool_result":
                    try:
                        resp = json.loads(b["content"]) if isinstance(b["content"], str) else b["content"]
                    except ValueError:
                        resp = {"text": b["content"]}
                    if not isinstance(resp, dict):
                        resp = {"result": resp}
                    parts.append({"functionResponse": {"name": b.get("name") or names.get(b["tool_use_id"], "tool"),
                                                       "response": resp}})
            if parts:
                out.append({"role": role, "parts": parts})
        return out

    def complete(self, system, messages, tools):
        if self.requests >= self.max_requests:
            raise ModelError(f"Gemini request budget exhausted ({self.max_requests}); stopping (no fallback)")
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": self.to_contents(messages),
                "tools": [{"functionDeclarations": [{"name": t["name"], "description": t["description"],
                                                     "parameters": gemini_schema(t["input_schema"])} for t in tools]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}}
        req = urllib.request.Request(GEMINI_URL.format(model=self.model), data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        t0 = time.time()
        self.requests += 1
        try:
            import ssl
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            self._log({"error": e.code, "detail": detail, "latency_s": round(time.time() - t0, 2)})
            if e.code == 429:
                raise ModelError(f"Gemini quota/rate limit reached (429). Stopping; no fallback. {detail}") from None
            raise ModelError(f"Gemini HTTP {e.code}: {detail}") from None
        dt = time.time() - t0
        um = data.get("usageMetadata", {})
        usage = Usage(um.get("promptTokenCount", 0), um.get("candidatesTokenCount", 0), um.get("thoughtsTokenCount", 0), 1)
        cand = (data.get("candidates") or [{}])[0]
        blocks = []
        for p in (cand.get("content") or {}).get("parts", []):
            if "functionCall" in p:
                fc = p["functionCall"]
                blocks.append({"type": "tool_use", "id": "gc_" + uuid.uuid4().hex[:10], "name": fc["name"],
                               "input": decode_args(fc.get("args") or {}),
                               "provider_meta": {"thoughtSignature": p["thoughtSignature"]} if p.get("thoughtSignature") else {}})
            elif p.get("text") and not p.get("thought"):
                blocks.append({"type": "text", "text": p["text"]})
        self._log({"model": data.get("modelVersion", self.model), "finish": cand.get("finishReason"),
                   "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                   "thinking_tokens": usage.thinking_tokens, "latency_s": round(dt, 2),
                   "tool_calls": [b["name"] for b in blocks if b["type"] == "tool_use"]})
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else (
            "max_tokens" if cand.get("finishReason") == "MAX_TOKENS" else "end_turn")
        return ModelResponse(blocks, stop, usage, data.get("modelVersion", self.model), dt)

    def _log(self, rec: dict) -> None:
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_log, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}) + "\n")


# ------------------------------------------------------------------ Anthropic (kept from Phase 2; opt-in only, paid)
class AnthropicBackend:
    """Anthropic Messages API. Paid provider: only constructed when explicitly requested AND AIRPORT_ALLOW_PAID=1."""
    name = "anthropic"

    def __init__(self, model: str | None = None, max_tokens: int = 4096):
        if os.environ.get("AIRPORT_ALLOW_PAID") != "1":
            raise ModelError("paid providers are disabled (set AIRPORT_ALLOW_PAID=1 to allow)")
        import anthropic  # noqa: deferred optional dependency
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("AIRPORT_AGENT_MODEL", "claude-opus-5-5")
        self.max_tokens = max_tokens

    def complete(self, system, messages, tools):
        t0 = time.time()
        clean = [{"role": m["role"], "content": [{k: v for k, v in b.items() if k not in ("provider_meta", "name")
                                                   or (k == "name" and b.get("type") == "tool_use")}
                                                  for b in m["content"]] if isinstance(m["content"], list) else m["content"]}
                 for m in messages]
        r = self.client.messages.create(model=self.model, system=system, messages=clean, tools=tools,
                                        max_tokens=self.max_tokens)
        u = Usage(r.usage.input_tokens, r.usage.output_tokens, 0, 1)
        return ModelResponse([b.model_dump() for b in r.content], r.stop_reason, u, self.model, time.time() - t0)


def backend_from_env() -> ModelBackend:
    """AIRPORT_MODEL=scripted|gemini. Defaults to an offline demo backend; never silently picks a paid provider."""
    kind = os.environ.get("AIRPORT_MODEL", "offline")
    if kind == "gemini":
        return GeminiBackend()
    if kind == "anthropic":
        return AnthropicBackend()
    from .offline import OfflineBackend
    return OfflineBackend()
