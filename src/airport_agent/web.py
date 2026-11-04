"""External web research, kept strictly apart from the internal evidence.

Tools (registered on the agent as extra tools):
  web_search {query, k}  -> candidate pages (title, url, snippet). Snippets are NOT evidence.
  fetch_page {url}       -> page title + readable text excerpt; registers external evidence W# (url, title, retrieved_at,
                            sha256 of the text). W# ids are a separate namespace from internal findings F#.
In compose_answer, external evidence is used through claims of kind "external": {kind, text, source: "W#", quote}.
The claim text may contain no numbers (as everywhere); a number from the web can appear only inside `quote`, which
must be a verbatim excerpt of the fetched page — verified server-side. {W#} in prose renders as a link to the page.

Safety: http(s) only, ports 80/443, hostnames resolving to private/loopback/link-local addresses are refused at every
redirect hop (SSRF guard), size and time limits, text extraction only (no scripts executed, nothing saved to disk
except the extracted text in the conversation store).
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import re
import socket
import ssl
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Callable, Protocol

UA = "AirportIntelResearch/0.3 (analyst tool; fetches single pages on request)"
MAX_BYTES = 2_000_000
MAX_TEXT = 200_000


class WebError(Exception):
    pass


# ------------------------------------------------------------------ fetching with an SSRF guard
def _check_host(url: str) -> None:
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise WebError("only http(s) URLs are allowed")
    if u.port not in (None, 80, 443):
        raise WebError("only ports 80/443 are allowed")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise WebError(f"cannot resolve {u.hostname}: {e}") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise WebError(f"refusing to fetch a non-public address ({u.hostname})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def http_get(url: str, timeout: float = 15.0, max_redirects: int = 4) -> tuple[str, bytes, str]:
    """-> (final_url, body, content_type). Each hop is re-checked by the SSRF guard."""
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=_ctx()))
    for _ in range(max_redirects + 1):
        _check_host(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1"})
        try:
            r = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            raise WebError(f"HTTP {e.code} for {url}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise WebError(f"fetch failed: {e}") from None
        with r:
            body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise WebError("page too large")
            return r.geturl(), body, r.headers.get("Content-Type", "")
    raise WebError("too many redirects")


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe", "template"}
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "tr", "br", "section", "article", "table", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.title, self._skip, self._in_title = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.out.append(data)


def extract_text(body: bytes, content_type: str) -> tuple[str, str]:
    m = re.search(r"charset=([\w-]+)", content_type or "")
    txt = body.decode(m.group(1) if m else "utf-8", "replace")
    if "html" not in (content_type or "html") and not txt.lstrip().startswith("<"):
        return "", re.sub(r"[ \t]+", " ", txt)[:MAX_TEXT]
    p = _Text()
    p.feed(txt)
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return html.unescape(p.title.strip())[:300], text[:MAX_TEXT]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace(" ", " ")).strip().lower()


# ------------------------------------------------------------------ search providers
class SearchProvider(Protocol):
    name: str

    def search(self, query: str, k: int) -> list[dict]: ...


class DuckDuckGoHTML:
    """Keyless HTML endpoint. If the provider refuses (rate limit / bot check), we report it; we never try to evade it."""
    name = "duckduckgo_html"

    def __init__(self, get: Callable[[str], tuple[str, bytes, str]] = http_get):
        self.get = get

    def search(self, query: str, k: int) -> list[dict]:
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        _, body, _ = self.get(url)
        page = body.decode("utf-8", "replace")
        out = []
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                             page, re.S):
            href, title, rest = m.groups()
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(href)).query)
            real = q.get("uddg", [html.unescape(href)])[0]
            if not real.startswith("http"):
                continue
            sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
            strip = lambda x: html.unescape(re.sub(r"<[^>]+>", "", x or "")).strip()  # noqa: E731
            out.append({"title": strip(title), "url": real, "snippet": strip(sn.group(1) if sn else "")[:300]})
            if len(out) >= k:
                break
        if not out:
            raise WebError("search provider returned no parsable results (possibly rate-limited); try again later")
        return out


# ------------------------------------------------------------------ the research toolset
class WebResearch:
    def __init__(self, items: dict[str, dict] | None = None, provider: SearchProvider | None = None,
                 get: Callable[[str], tuple[str, bytes, str]] = http_get, max_fetches_per_turn: int = 6):
        self.items = items if items is not None else {}            # W# -> record (shared with Session.web)
        self.provider = provider or DuckDuckGoHTML(get)
        self.get = get
        self.max_fetches = max_fetches_per_turn
        self._fetches = 0

    def new_turn(self) -> None:
        self._fetches = 0

    def _next_id(self) -> str:
        return f"W{max((int(k[1:]) for k in self.items), default=0) + 1}"

    def web_search(self, a: dict) -> dict:
        q = str(a.get("query") or "").strip()
        if not q:
            return {"error": "invalid_request", "message": "query required"}
        k = max(1, min(int(a.get("k") or 5), 8))
        try:
            res = self.provider.search(q[:300], k)
        except WebError as e:
            return {"error": "web_unavailable", "message": str(e)}
        return {"provider": self.provider.name, "results": res,
                "note": "snippets are not evidence: call fetch_page on a result to read and cite it"}

    def fetch_page(self, a: dict) -> dict:
        url = str(a.get("url") or "").strip()
        if self._fetches >= self.max_fetches:
            return {"error": "budget", "message": f"at most {self.max_fetches} page fetches per question"}
        for wid, it in self.items.items():                         # same page already in this conversation
            if it["url"] == url:
                return self._view(wid, it)
        self._fetches += 1
        try:
            final, body, ctype = self.get(url)
        except WebError as e:
            return {"error": "fetch_failed", "message": str(e)}
        title, text = extract_text(body, ctype)
        if len(text) < 200:
            return {"error": "no_text", "message": "the page has no readable text (scripts-only or non-HTML)"}
        wid = self._next_id()
        it = {"id": wid, "kind": "external_web", "url": final, "requested_url": url, "title": title or final,
              "domain": urllib.parse.urlsplit(final).hostname, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text), "text": text}
        self.items[wid] = it
        return self._view(wid, it)

    @staticmethod
    def _view(wid: str, it: dict) -> dict:
        return {"id": wid, "title": it["title"], "url": it["url"], "domain": it["domain"], "retrieved_at": it["retrieved_at"],
                "excerpt": it["text"][:6000], "truncated": it["chars"] > 6000,
                "how_to_cite": f"claims: {{kind: 'external', text (no numbers), source: '{wid}', quote: '<verbatim words from "
                               f"the page>'}}; {{{wid}}} in prose renders as a link. External sources are not internal findings."}

    def tools(self) -> dict[str, tuple[dict, Callable]]:
        return {
            "web_search": ({"name": "web_search", "description":
                            "Search the public web for context the internal datasets do not contain (e.g. announced terminal "
                            "projects, capacity programs, airline announcements). Returns candidate pages; snippets are not "
                            "evidence. Prefer internal data for any metric it covers.",
                            "input_schema": {"type": "object", "properties": {"query": {"type": "string"},
                                                                              "k": {"type": "integer"}}, "required": ["query"]}},
                           self.web_search),
            "fetch_page": ({"name": "fetch_page", "description":
                            "Fetch one public web page and return its readable text; registers it as external evidence W#. "
                            "Cite it with a claim {kind:'external', text, source:'W#', quote:'verbatim excerpt'}; a number from "
                            "the web may appear only inside the verbatim quote.",
                            "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
                           self.fetch_page),
        }


def public_record(it: dict) -> dict:
    """What the UI/inspector sees (no full page text)."""
    return {k: it[k] for k in ("id", "kind", "url", "requested_url", "title", "domain", "retrieved_at", "sha256", "chars")} | {
        "excerpt": it["text"][:1500]}

