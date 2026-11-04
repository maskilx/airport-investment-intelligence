"""Minimal, defensive HTTP client (stdlib only).

Lessons from Phase 0 encoded here:
  * BTS silently truncates large downloads -> verify Content-Length.
  * Never resume partial files (a resume once grafted two files together) ->
    every attempt downloads from byte 0 into memory; nothing partial is kept.
"""
from __future__ import annotations

import http.cookiejar
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "airport-intel-data/0.1 (research pipeline; python-urllib)"


class FetchError(RuntimeError):
    pass


@dataclass
class Response:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


@dataclass
class HttpClient:
    timeout: float = 600.0
    retries: int = 3
    backoff: float = 5.0
    user_agent: str = USER_AGENT
    _opener: urllib.request.OpenerDirector = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # cookie-aware (ASP.NET forms need the session cookie between GET and POST);
        # certifi CA bundle when available (python.org macOS builds ship without one)
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            urllib.request.HTTPSHandler(context=ctx),
        )

    def request(self, url: str, data: dict[str, str] | None = None) -> Response:
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers={"User-Agent": self.user_agent})
                with self._opener.open(req, timeout=self.timeout) as r:
                    payload = r.read()
                    headers = {k.lower(): v for k, v in r.headers.items()}
                    expected = headers.get("content-length")
                    if expected is not None and int(expected) != len(payload):
                        raise FetchError(f"truncated: got {len(payload)} of {expected} bytes")
                    return Response(r.geturl(), r.status, headers, payload)
            except (urllib.error.URLError, TimeoutError, ConnectionError, FetchError) as e:
                last = e
                if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429:
                    break  # client errors are not transient
                if attempt < self.retries:
                    time.sleep(self.backoff * attempt)
        raise FetchError(f"{url}: {last}") from last

    def get(self, url: str) -> Response:
        return self.request(url)

    def post(self, url: str, data: dict[str, str]) -> Response:
        return self.request(url, data)
