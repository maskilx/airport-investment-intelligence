"""Voice: another interface to the SAME agent (docs/voice-architecture-review.md).

Chained pipeline: browser VAD / recognition -> (optional) server speech-to-text -> the existing message endpoint (same
conversation, memory, tools, validation) -> a deterministic spoken rendering of the VALIDATED answer -> browser TTS.
Nothing here plans, calls tools or writes answers. Provider keys stay on the server.

Speech-to-text providers:
  browser (default) - Web Speech recognition in the browser; no key, no server call (Chrome/Safari; audio goes to
                      the browser vendor's service)
  groq              - Groq whisper-large-v3-turbo on the server (AIRPORT_VOICE_STT=groq + Groq key); separate daily
                      budget (AIRPORT_VOICE_MAX_REQUESTS) and usage log; utterances are de-duplicated by id
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Protocol

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_AUDIO_BYTES = 5_000_000            # ~2.5 min of 16 kHz mono WAV; an utterance is seconds


class VoiceError(Exception):
    pass


class Transcriber(Protocol):
    name: str

    def transcribe(self, wav: bytes) -> str: ...


class FakeTranscriber:
    """Deterministic transcriber for offline tests and demos without a key."""
    name = "fake"

    def __init__(self, text: str = "Compare congestion at LAX and SNA."):
        self.text, self.calls = text, 0

    def transcribe(self, wav: bytes) -> str:
        self.calls += 1
        return self.text


class GroqWhisper:
    name = "groq-whisper"

    def __init__(self, api_key: str, model: str | None = None, usage_log: str | Path | None = None,
                 max_requests: int | None = None):
        from airport_data.config import get_paths
        self.api_key, self.model = api_key, model or os.environ.get("AIRPORT_VOICE_STT_MODEL", "whisper-large-v3-turbo")
        self.usage_log = Path(usage_log or get_paths().app / "voice_usage.jsonl")
        self.max_requests = int(max_requests or os.environ.get("AIRPORT_VOICE_MAX_REQUESTS", 150))
        self._lock = threading.Lock()
        day = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            self.requests = sum(1 for ln in open(self.usage_log) if f'"utc_day": "{day}"' in ln)
        except FileNotFoundError:
            self.requests = 0

    def transcribe(self, wav: bytes) -> str:
        with self._lock:
            if self.requests >= self.max_requests:
                raise VoiceError(f"voice daily request budget exhausted ({self.max_requests})")
            self.requests += 1
        b = "----airport" + uuid.uuid4().hex
        parts = []
        for k, v in (("model", self.model), ("language", "en"), ("response_format", "json"), ("temperature", "0")):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="utterance.wav"\r\n'
                     f"Content-Type: audio/wav\r\n\r\n".encode() + wav + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(GROQ_STT_URL, data=b"".join(parts), headers={
            "Content-Type": f"multipart/form-data; boundary={b}", "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "airport-intel"})
        t0 = time.time()
        try:
            import ssl
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                text = (json.loads(r.read()).get("text") or "").strip()
        except urllib.error.HTTPError as e:
            self._log({"error": e.code})
            raise VoiceError(f"speech-to-text failed (HTTP {e.code})") from None
        except Exception as e:
            self._log({"error": type(e).__name__})
            raise VoiceError(f"speech-to-text unavailable ({type(e).__name__})") from None
        self._log({"model": self.model, "bytes": len(wav), "latency_s": round(time.time() - t0, 2), "chars": len(text)})
        return text

    def _log(self, rec: dict) -> None:
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_log, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "utc_day": time.strftime("%Y-%m-%d", time.gmtime()), **rec}) + "\n")


def transcriber_from_env() -> Transcriber | None:
    """Server STT only on explicit opt-in (it spends Groq quota); otherwise the browser recognises speech."""
    if os.environ.get("AIRPORT_VOICE_STT", "browser").lower() != "groq":
        return None
    from airport_data.config import load_groq_key
    key = load_groq_key()
    if not key:
        raise VoiceError("AIRPORT_VOICE_STT=groq but no Groq key: run ./scripts/configure-groq-key.sh")
    return GroqWhisper(key)


class Dedup:
    """Remembers recent ids (utterances, client turns) so reconnects and double-fires never create duplicate turns."""

    def __init__(self, size: int = 512):
        self._d: OrderedDict[str, object] = OrderedDict()
        self._lock = threading.Lock()
        self.size = size

    def seen(self, key: str) -> object | None:
        with self._lock:
            return self._d.get(key)

    def remember(self, key: str, value: object = True) -> None:
        with self._lock:
            self._d[key] = value
            self._d.move_to_end(key)
            while len(self._d) > self.size:
                self._d.popitem(last=False)


def is_wav(b: bytes) -> bool:
    return len(b) > 44 and b[:4] == b"RIFF" and b[8:12] == b"WAVE"


_RANGE = re.compile(r"(\d{4})-(\d{2})…(\d{4})-(\d{2})")


def speakable(text: str) -> str:
    """Rendered (validated) text made easier to listen to: no markdown, ranges and symbols in words."""
    t = re.sub(r"[*_`#|\[\]]", "", text or "")
    t = re.sub(r"\(\s*\)", "", t)
    t = _RANGE.sub(lambda m: f"{m.group(1)}-{m.group(2)} to {m.group(3)}-{m.group(4)}", t)
    t = t.replace("…", " to ").replace("≥", "at least ").replace("—", ", ").replace("→", " to ")
    return re.sub(r"\s+", " ", t).strip()
