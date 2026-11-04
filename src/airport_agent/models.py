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
import re
import threading
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


FREE_TIER_MODEL = re.compile(r"^gemini-[0-9.]+-flash(?:-lite)?(?:-[a-z0-9.-]+)?$")


class GeminiBackend:
    """Google Gemini API generateContent with function calling. No SDK dependency; explicit, auditable requests."""
    name = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None, max_requests: int | None = None,
                 usage_log: str | Path | None = None, timeout: float = 120.0):
        if os.environ.get("AIRPORT_ALLOW_GEMINI") != "1":
            raise ModelError("Gemini calls are disabled (set AIRPORT_ALLOW_GEMINI=1 to allow real API calls)")
        from airport_data.config import load_gemini_key
        self.api_key = api_key or load_gemini_key()
        if not self.api_key:
            raise ModelError("no Gemini API key: run ./scripts/configure-gemini-key.sh (stores it in the macOS Keychain)")
        self.model = model or os.environ.get("AIRPORT_GEMINI_MODEL", "gemini-3.8-flash")
        if not FREE_TIER_MODEL.match(self.model) and os.environ.get("AIRPORT_ALLOW_PAID") != "1":
            raise ModelError(f"model {self.model!r} is not a free-tier Flash model; set AIRPORT_ALLOW_PAID=1 to allow it")
        self.max_requests = int(max_requests or os.environ.get("AIRPORT_GEMINI_MAX_REQUESTS", 25))
        from airport_data.config import get_paths            # anchored to the data dir, not the current directory,
        self.usage_log = Path(usage_log or os.environ.get("AIRPORT_GEMINI_USAGE_LOG")   # so the daily budget always
                              or get_paths().app / "gemini_usage.jsonl")              # reads the same log
        self.timeout = timeout
        self._lock = threading.Lock()
        self.requests = self._requests_today()     # the budget is per UTC day and survives restarts

    def _requests_today(self) -> int:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            with open(self.usage_log) as f:
                return sum(1 for line in f if f'"utc_day": "{day}"' in line and '"request": true' in line)
        except FileNotFoundError:
            return 0

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
        with self._lock:                                 # concurrent conversations share one budget
            if self.requests >= self.max_requests:
                raise ModelError(f"Gemini daily request budget exhausted ({self.max_requests}); stopping (no fallback)")
            self.requests += 1
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": self.to_contents(messages),
                "tools": [{"functionDeclarations": [{"name": t["name"], "description": t["description"],
                                                     "parameters": gemini_schema(t["input_schema"])} for t in tools]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}}
        req = urllib.request.Request(GEMINI_URL.format(model=self.model), data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        t0 = time.time()
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
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "utc_day": time.strftime("%Y-%m-%d", time.gmtime()),
                                "request": True, **rec}) + "\n")


# ------------------------------------------------------------------ Anthropic (kept from Phase 2; opt-in only, paid)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Tool-capable chat models available outside Groq Enterprise (docs/model-provider-review.md). Others are refused.
GROQ_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b")


def _secs(v: str | None) -> float:
    """Groq reset headers look like '7.66s', '1m2.5s' or '450ms'."""
    if not v:
        return 0.0
    total = 0.0
    for num, unit in re.findall(r"([\d.]+)(ms|h|m|s)", v):
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total


class GroqBackend:
    """Groq (OpenAI-compatible chat completions) with function calling. Same agent loop, tools and validation as every
    other backend. Separate key (macOS Keychain service 'airport-investment-intelligence-groq'), separate daily budget
    and usage log, no fallback. Free-tier aware: a smaller per-request context cap (AIRPORT_GROQ_MAX_CONTEXT_TOKENS) and
    proactive pacing from Groq's x-ratelimit headers, so requests wait for the token window instead of failing."""
    name = "groq"

    def __init__(self, model: str | None = None, api_key: str | None = None, max_requests: int | None = None,
                 usage_log: str | Path | None = None, timeout: float = 120.0, sleep=time.sleep):
        if os.environ.get("AIRPORT_ALLOW_GROQ") != "1":
            raise ModelError("Groq calls are disabled (set AIRPORT_ALLOW_GROQ=1, e.g. ./scripts/mode.sh groq)")
        from airport_data.config import get_paths, load_groq_key
        self.api_key = api_key or load_groq_key()
        if not self.api_key:
            raise ModelError("no Groq API key: run ./scripts/configure-groq-key.sh (stores it in the macOS Keychain)")
        self.model = model or os.environ.get("AIRPORT_GROQ_MODEL", "openai/gpt-oss-120b")
        if self.model not in GROQ_MODELS:
            raise ModelError(f"Groq model {self.model!r} is not one of the supported tool-calling models {list(GROQ_MODELS)}")
        self.max_requests = int(max_requests or os.environ.get("AIRPORT_GROQ_MAX_REQUESTS", 60))
        self.usage_log = Path(usage_log or os.environ.get("AIRPORT_GROQ_USAGE_LOG") or get_paths().app / "groq_usage.jsonl")
        self.max_context_tokens = int(os.environ.get("AIRPORT_GROQ_MAX_CONTEXT_TOKENS", 8000))
        self.max_completion_tokens = int(os.environ.get("AIRPORT_GROQ_MAX_COMPLETION_TOKENS", 1500))
        self.timeout, self._sleep = timeout, sleep
        self._lock = threading.Lock()
        self.requests = self._requests_today()
        self.rate: dict[str, float] = {}

    def _requests_today(self) -> int:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            with open(self.usage_log) as f:
                return sum(1 for line in f if f'"utc_day": "{day}"' in line and '"request": true' in line)
        except FileNotFoundError:
            return 0

    @staticmethod
    def to_messages(system: str, messages: list[dict]) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for m in messages:
            blocks = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
            if m["role"] == "assistant":
                text = "\n".join(b.get("text", "") for b in blocks if b["type"] == "text").strip()
                calls = [{"id": b["id"], "type": "function",
                          "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                         for b in blocks if b["type"] == "tool_use"]
                msg: dict[str, Any] = {"role": "assistant", "content": text or None}
                if calls:
                    msg["tool_calls"] = calls
                out.append(msg)
                continue
            texts = []
            for b in blocks:
                if b["type"] == "tool_result":
                    c = b["content"] if isinstance(b["content"], str) else json.dumps(b["content"])
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": c})
                elif b["type"] == "text" and b.get("text"):
                    texts.append(b["text"])
            if texts:
                out.append({"role": "user", "content": "\n".join(texts)})
        return out

    @staticmethod
    def to_tools(tools: list[dict]) -> list[dict]:
        # same schema translation as Gemini: oneOf / free-form objects become JSON strings, decoded by decode_args
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                  "parameters": gemini_schema(t["input_schema"])}} for t in tools]

    def _pace(self, est_tokens: int) -> None:
        """Proactive rate pacing (not a retry): if the last response said the token window cannot take this request,
        wait for the window to reset (bounded)."""
        rem, reset = self.rate.get("remaining_tokens"), self.rate.get("reset_tokens_s", 0.0)
        if rem is not None and est_tokens + self.max_completion_tokens > rem and reset > 0:
            self._sleep(min(reset + 0.5, 65.0))

    def complete(self, system, messages, tools):
        body = {"model": self.model, "messages": self.to_messages(system, messages), "tools": self.to_tools(tools),
                "tool_choice": "auto", "parallel_tool_calls": False, "temperature": 0.2,
                "max_completion_tokens": self.max_completion_tokens}
        if self.model.startswith("openai/gpt-oss"):
            body.update({"reasoning_effort": "medium", "include_reasoning": False})
        data_bytes = json.dumps(body).encode()
        self._pace(len(data_bytes) // 4)
        with self._lock:
            if self.requests >= self.max_requests:
                raise ModelError(f"Groq daily request budget exhausted ({self.max_requests}); stopping (no fallback)")
            self.requests += 1
        req = urllib.request.Request(GROQ_URL, data=data_bytes, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}", "User-Agent": "airport-intel"})
        t0 = time.time()
        try:
            import ssl
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as r:
                hdr = {k.lower(): v for k, v in r.headers.items()}
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500].replace(self.api_key, "[key]")
            self._log({"error": e.code, "detail": detail, "latency_s": round(time.time() - t0, 2)})
            if e.code == 429:
                raise ModelError(f"Groq rate limit reached (429). Stopping; no fallback. {detail}") from None
            if e.code == 413:
                raise ModelError(f"Groq request too large for this account's token-per-minute limit (413). Lower "
                                 f"AIRPORT_GROQ_MAX_CONTEXT_TOKENS or use a paid tier. {detail}") from None
            raise ModelError(f"Groq HTTP {e.code}: {detail}") from None
        self.rate = {"remaining_tokens": float(hdr.get("x-ratelimit-remaining-tokens") or 0) if hdr.get(
            "x-ratelimit-remaining-tokens") is not None else None,
                     "reset_tokens_s": _secs(hdr.get("x-ratelimit-reset-tokens")),
                     "limit_tokens": float(hdr.get("x-ratelimit-limit-tokens") or 0) or None,
                     "limit_requests_day": float(hdr.get("x-ratelimit-limit-requests") or 0) or None}
        dt = time.time() - t0
        u = data.get("usage") or {}
        usage = Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 0, 1)
        ch = (data.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        blocks = []
        if msg.get("content"):
            blocks.append({"type": "text", "text": msg["content"]})
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            try:
                args = decode_args(json.loads(fn.get("arguments") or "{}"))
            except ValueError:
                args = {"__invalid_arguments__": (fn.get("arguments") or "")[:500]}
            blocks.append({"type": "tool_use", "id": tc.get("id") or "gq_" + uuid.uuid4().hex[:10],
                           "name": fn.get("name", ""), "input": args})
        self._log({"model": data.get("model", self.model), "finish": ch.get("finish_reason"),
                   "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "latency_s": round(dt, 2),
                   "tool_calls": [b["name"] for b in blocks if b["type"] == "tool_use"],
                   "ratelimit": {k: v for k, v in self.rate.items() if v is not None}})
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else (
            "max_tokens" if ch.get("finish_reason") == "length" else "end_turn")
        return ModelResponse(blocks, stop, usage, data.get("model", self.model), dt)

    def _log(self, rec: dict) -> None:
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_log, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "utc_day": time.strftime("%Y-%m-%d", time.gmtime()),
                                "request": True, **rec}) + "\n")


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
    kind = os.environ.get("AIRPORT_MODEL", "offline").strip().lower()
    if kind == "gemini":
        return GeminiBackend()
    if kind == "groq":
        return GroqBackend()
    if kind == "anthropic":
        return AnthropicBackend()
    if kind == "offline":
        from .offline import OfflineBackend
        return OfflineBackend()
    # an invalid configuration must fail loudly, not silently demo the offline planner as if it were the LLM
    raise ModelError(f"unknown AIRPORT_MODEL={kind!r} (expected offline | gemini | groq | anthropic)")
