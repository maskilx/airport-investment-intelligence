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
