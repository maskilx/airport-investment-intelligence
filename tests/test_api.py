"""HTTP API with the offline planner (no model calls): SSE stream, reload, provenance, memory inspector."""
import json

import pytest

from airport_data.config import get_paths

pytestmark = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")


@pytest.fixture()
def client(tmp_path):
    from fastapi.testclient import TestClient

    from airport_agent.offline import OfflineBackend
    from airport_app.server import App, create_app
    return TestClient(create_app(App(str(tmp_path / "conv.sqlite"), backend=OfflineBackend())))


def _events(resp):
    out = []
    for chunk in resp.text.split("\n\n"):
        lines = dict(l.split(": ", 1) for l in chunk.strip().splitlines() if ": " in l)
        if "data" in lines:
            out.append(json.loads(lines["data"]))
    return out


def test_health_reports_offline_backend(client):
    h = client.get("/api/health").json()
    assert h["backend"] == "offline" and h["llm"] is False and h["catalog_version"]


def test_stream_answer_then_reload_and_inspect(client):
    cid = client.post("/api/conversations").json()["id"]
    r = client.post(f"/api/conversations/{cid}/messages", json={"text": "Compare LA and Santa Ana airport congestion levels."})
    assert r.headers["content-type"].startswith("text/event-stream")
    ev = _events(r)
    types = [e["type"] for e in ev]
    assert types[0] == "turn_started" and types[-1] == "done" and "tool_finished" in types
    ans = next(e for e in ev if e["type"] == "answer")
    assert ans["kind"] == "answer" and ans["charts"] and ans["structured"]["headline"].startswith("Congestion")
    fid = ans["cited"][0]
    # reload
    conv = client.get(f"/api/conversations/{cid}").json()
    assert conv["title"].startswith("Compare LA") and conv["turns"][0]["answer"]["markdown"] == ans["markdown"]
    # provenance: links come from the source catalog / ingest manifest
    f = client.get(f"/api/conversations/{cid}/findings/{fid}").json()
    sd = f["sources_detail"][0]
    assert sd["homepage"].startswith("http") and sd["vintages"] and f["formatted"]
    assert all(u.startswith("http") for u in sd["download_urls"])
    assert client.get(f"/api/conversations/{cid}/findings/F99999").status_code == 404
    # memory inspector
    m = client.get(f"/api/conversations/{cid}/memory").json()
    assert {e["key"] for e in m["state"]["entities"]} >= {"LAX", "SNA"} and m["findings_total"] > 0
    assert client.get("/api/conversations").json()[0]["id"] == cid


def test_follow_up_over_http_uses_memory(client):
    cid = client.post("/api/conversations").json()["id"]
    _events(client.post(f"/api/conversations/{cid}/messages", json={"text": "What is the seat factor at SFO?"}))
    ev = _events(client.post(f"/api/conversations/{cid}/messages", json={"text": "and the delay rate there?"}))
    ans = next(e for e in ev if e["type"] == "answer")
    assert ans["kind"] == "answer" and "SFO" in ans["markdown"]
    ctx = next(e for e in ev if e["type"] == "context")
    assert ctx["turns_verbatim"] == 1 and ctx["memory_tokens"] > 0


def test_unknown_conversation_and_validation(client):
    assert client.get("/api/conversations/nope").status_code == 404
    cid = client.post("/api/conversations").json()["id"]
    assert client.post(f"/api/conversations/{cid}/messages", json={"text": ""}).status_code == 422
    assert client.get("/api/sources").json()[0]["homepage"]


# ---------------------------------------------------------------- text turns: follow-up context, retry de-duplication
def test_follow_up_keeps_context_and_a_retried_turn_runs_once(client):
    cid = client.post("/api/conversations").json()["id"]
    q = "Compare LA and Santa Ana airport congestion levels."
    ev = _events(client.post(f"/api/conversations/{cid}/messages", json={"text": q, "client_turn_id": "t1"}))
    ans = next(e for e in ev if e["type"] == "answer")
    assert ans["kind"] == "answer" and any(e["type"] == "tool_finished" and e["name"] == "run_analysis" for e in ev)
    assert [e["type"] for e in ev].index("tool_started") < [e["type"] for e in ev].index("answer")   # progress first
    dup = _events(client.post(f"/api/conversations/{cid}/messages", json={"text": q, "client_turn_id": "t1"}))
    assert [e["type"] for e in dup] == ["duplicate", "done"]                          # a resent turn is not run twice
    follow = _events(client.post(f"/api/conversations/{cid}/messages",
                                 json={"text": "What about their passenger trend over time?", "client_turn_id": "t2"}))
    f_ans = next(e for e in follow if e["type"] == "answer")
    assert "LAX" in f_ans["structured"]["headline"] and "SNA" in f_ans["structured"]["headline"]
    assert len(client.get(f"/api/conversations/{cid}").json()["turns"]) == 2


# ---------------------------------------------------------------- live public API (FAA NAS Status), fixture only
def test_live_faa_status_is_external_evidence_with_verbatim_quotes(monkeypatch):
    from pathlib import Path

    from airport_agent import live_status
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    xml = (Path(__file__).parent / "fixtures" / "nas_status.xml").read_text()
    monkeypatch.setattr(live_status.LiveStatus, "_http", lambda self: xml)
    a = Agent(OfflineBackend())
    r = a.ask("How congested are LAX and SAN right now?")
    assert r.kind == "answer", r.markdown
    ext = [c for c in r.structured["claims"] if c["kind"] == "external"]
    assert ext and all(c["source"].startswith("W") for c in ext)
    w = a.web_evidence[ext[0]["source"]]
    assert w["url"] == live_status.NAS_STATUS_URL and w["kind"] == "external_api" and ext[0]["quote"] in w["text"]
    assert any(e["title"].startswith("FAA NAS Status") for e in r.structured["external"])
    # an ordinary (historical) congestion question never calls the live API
    calls = []
    monkeypatch.setattr(live_status.LiveStatus, "_http", lambda self: calls.append(1) or xml)
    Agent(OfflineBackend()).ask("Compare LA and Santa Ana airport congestion levels.")
    assert not calls


def test_live_status_parser_refuses_entities_and_lists_quiet_airports():
    from airport_agent.live_status import parse, render_lines
    with pytest.raises(ValueError):
        parse('<!DOCTYPE x [<!ENTITY a "b">]><AIRPORT_STATUS_INFORMATION/>')
    u, items = parse("<AIRPORT_STATUS_INFORMATION><Update_Time>T</Update_Time></AIRPORT_STATUS_INFORMATION>")
    assert render_lines(u, items, ["BOS"])[1].startswith("BOS: no ground delay program")


def test_source_links_are_labelled_by_what_they_open():
    from airport_agent.provenance import link_for
    assert link_for("faa_taf", "https://taf.faa.gov/Downloads/APO100_TAF_Final_2025.zip")[0]["label"] == "raw file"
    t100 = link_for("bts_t100_segment", "https://www.transtats.bts.gov/DL_SelectFields.aspx?x")
    assert t100[0]["label"] == "download form" and t100[0]["note"]
    assert link_for("faa_atads_ops", "https://www.aspm.faa.gov/opsnet/sys/opsnet-server-x.asp")[0]["url"].endswith("airport.asp")
    assert link_for("bts_lookups", "https://www.transtats.bts.gov/Download_Lookup.asp") == []
    assert [x["url"].rsplit("/", 1)[1] for x in link_for("ourairports", "https://davidmegginson.github.io/ourairports-data/")] == \
        ["airports.csv", "runways.csv"]
    assert link_for("curated_constraints", "file://airport_constraints.csv") == []
