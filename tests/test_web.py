"""External web research: SSRF guard, extraction, verbatim-quote grounding, separation from findings (no network)."""
import socket

import pytest

from airport_agent import web as W
from airport_agent.web import DuckDuckGoHTML, WebError, WebResearch, extract_text
from airport_analytics.evidence import EvidenceStore
from airport_analytics.render import render, validate
from airport_data.config import get_paths

PAGE = b"""<html><head><title>SFO Terminal Program</title><script>var x=99;</script></head><body>
<nav>menu 123</nav><h1>Harvey Milk Terminal 1</h1><p>The airport completed the final phase of the $2.4 billion
Terminal 1 program in 2024, adding nine gates.</p><p>""" + b"Filler sentence about the program. " * 20 + b"</p></body></html>"


def fake_get(url):
    if "duckduckgo" in url:
        return url, (b'<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fsfo">'
                     b'SFO <b>Terminal</b></a><a class="result__snippet" href="x">Terminal 1 program</a>'), "text/html"
    return "https://example.org/sfo", PAGE, "text/html; charset=utf-8"


def test_extract_text_drops_scripts_and_nav():
    title, text = extract_text(PAGE, "text/html")
    assert title == "SFO Terminal Program" and "$2.4 billion" in text and "var x" not in text and "menu 123" not in text


@pytest.mark.parametrize("host,ip", [("localhost", "127.0.0.1"), ("intranet", "10.0.0.5"), ("meta", "169.254.169.254"),
                                     ("v6", "::1")])
def test_ssrf_guard_rejects_private_addresses(monkeypatch, host, ip):
    fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
    monkeypatch.setattr(W.socket, "getaddrinfo", lambda *a, **k: [(fam, 1, 6, "", (ip, 80))])
    with pytest.raises(WebError, match="non-public"):
        W._check_host(f"http://{host}/")


def test_ssrf_guard_rejects_schemes_and_ports():
    for u in ("file:///etc/passwd", "ftp://example.org/", "http://example.org:8080/"):
        with pytest.raises(WebError):
            W._check_host(u)


def test_search_and_fetch_register_external_evidence():
    wr = WebResearch(get=fake_get)
    res = wr.web_search({"query": "SFO terminal program"})
    assert res["results"][0]["url"] == "https://example.org/sfo" and "not evidence" in res["note"]
    p = wr.fetch_page({"url": "https://example.org/sfo"})
    assert p["id"] == "W1" and wr.items["W1"]["sha256"] and "$2.4 billion" in p["excerpt"]
    assert wr.fetch_page({"url": "https://example.org/sfo"})["id"] == "W1"          # no duplicate ids for one page
    wr.max_fetches = 1
    assert wr.fetch_page({"url": "https://example.org/other"})["error"] == "budget"


def test_provider_refusal_is_reported_not_evaded():
    p = DuckDuckGoHTML(lambda url: (url, b"<html>anomaly detected</html>", "text/html"))
    with pytest.raises(WebError, match="rate-limited"):
        p.search("x", 3)


def _web():
    wr = WebResearch(get=fake_get)
    wr.fetch_page({"url": "https://example.org/sfo"})
    return wr.items


def test_external_claim_requires_verbatim_quote_and_keeps_numbers_in_quote():
    web, ev = _web(), EvidenceStore()
    ok = {"headline": "Terminal programs at SFO", "body": "See {W1}.",
          "claims": [{"kind": "external", "text": "SFO completed a terminal program", "source": "W1",
                      "quote": "completed the final phase of the $2.4 billion Terminal 1 program in 2024"}]}
    assert validate(ok, ev, None, web) == []
    out = render(ok, ev, None, web)
    assert "$2.4 billion" in out["markdown"] and "example.org" in out["markdown"]
    assert out["structured"]["external"][0]["id"] == "W1" and out["structured"]["claims"][0]["source"] == "W1"
    invented = dict(ok, claims=[dict(ok["claims"][0], quote="a $3 billion program")])
    assert any("not a verbatim excerpt" in e for e in validate(invented, ev, None, web))
    number_in_text = dict(ok, claims=[dict(ok["claims"][0], text="SFO spent $2.4 billion")])
    assert any("literal" in e for e in validate(number_in_text, ev, None, web))
    unknown = dict(ok, body="See {W7}.")
    assert any("W7" in e for e in validate(unknown, ev, None, web))


@pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")
def test_agent_web_flow_persists_w_ids_separately(tmp_path):
    from airport_agent.memory import ConversationStore
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent
    tu = lambda i, n, a: {"type": "tool_use", "id": f"t{i}", "name": n, "input": a}  # noqa: E731
    answer = {"answer": {"headline": "SFO terminal context", "body": "Internal data: {F1}. Web: {W1}.",
                         "claims": [{"kind": "fact", "text": "SFO seat factor {F1}", "support": ["F1"]},
                                    {"kind": "external", "text": "SFO finished a terminal program", "source": "W1",
                                     "quote": "adding nine gates"}]}}
    st = ConversationStore(tmp_path / "c.sqlite")
    a = Agent(ScriptedBackend([
        [tu(1, "run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}}}),
         tu(2, "web_search", {"query": "SFO terminal"})],
        [tu(3, "fetch_page", {"url": "https://example.org/sfo"})],
        [tu(4, "compose_answer", answer)]]), store=st, conv_id="c", web=WebResearch(get=fake_get))
    r = a.ask("What is SFO's seat factor and is it building terminals?")
    assert r.kind == "answer" and r.cited_findings == ["F1"] and r.structured["external"][0]["url"] == "https://example.org/sfo"
    assert "fetch_page" in [t["name"] for t in a.tools()]
    b = Agent(ScriptedBackend([]), store=ConversationStore(tmp_path / "c.sqlite"), conv_id="c")
    assert list(b.web_evidence) == ["W1"] and "F1" in b.evidence                     # both namespaces persist, separately
