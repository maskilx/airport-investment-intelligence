"""The bundled demo dataset (demo/snapshot): portable, faithful to the full database for its airports, and refusing
analyses outside its scope instead of answering them partially. Offline; no model calls."""
import duckdb
import pytest

from airport_agent.offline import OfflineBackend
from airport_agent.runtime import Agent
from airport_analytics.analysis import DEMO_NOTE
from airport_analytics.engine import Engine
from airport_analytics.tools import Session
from airport_data.config import get_paths
from airport_data.demo import SNAPSHOT, import_snapshot

needs_snapshot = pytest.mark.skipif(not (SNAPSHOT / "schema.sql").exists(), reason="demo snapshot not present")
QUESTIONS = ["Which airports in New England are strong candidates for terminal expansion?",
             "Compare LA and Santa Ana airport congestion levels.",
             "What is the percentage of long-haul flights out of Anchorage airport?",
             "What is the unmet flight demand in SFO airport and why?"]


@pytest.fixture(scope="module")
def demo_con(tmp_path_factory):
    if not (SNAPSHOT / "schema.sql").exists():
        pytest.skip("demo snapshot not present")
    db = import_snapshot(db_file=tmp_path_factory.mktemp("demo") / "airport.duckdb")
    return duckdb.connect(str(db), read_only=True)


def _agent(con):
    return Agent(OfflineBackend(), session=Session(Engine(con)), live_status=False)


@needs_snapshot
def test_snapshot_is_portable():
    load = (SNAPSHOT / "load.sql").read_text()
    assert "FROM '/" not in load and "/Users/" not in load            # relative Parquet names only


@needs_snapshot
def test_four_questions_answer_on_the_demo_dataset_with_a_demo_note(demo_con):
    for q in QUESTIONS:
        r = _agent(demo_con).ask(q)
        assert r.kind == "answer", (q, r.markdown[:300])
        assert DEMO_NOTE in r.markdown


@needs_snapshot
@pytest.mark.skipif(not get_paths().db_file.exists(), reason="full database required for the comparison")
def test_demo_values_match_the_full_database(demo_con):
    full = duckdb.connect(str(get_paths().db_file), read_only=True)
    for q in QUESTIONS:
        vals = []
        for con in (full, demo_con):
            a = _agent(con)
            a.ask(q)
            vals.append(sorted((f.label, f.value) for f in a.evidence.all()))
        assert vals[0] == vals[1], q


@needs_snapshot
def test_outside_the_demo_scope_is_refused_not_answered_partially(demo_con):
    s = Session(Engine(demo_con))
    r = s.call("run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["ORD"]}}})
    assert r["error"] == "out_of_coverage" and "ORD" in str(r)
    r = s.call("run_analysis", {"spec": {"op": "screen", "entities": {"group": {"state": "CA"}}}})
    assert r["error"] == "out_of_coverage"                              # CA has airports beyond LAX, SNA, SFO
    ok = s.call("run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}}})
    assert not ok.get("error")


@needs_snapshot
def test_out_of_scope_answer_explains_why(demo_con):
    r = _agent(demo_con).ask("How busy is ORD?")
    assert "outside the demo dataset" in r.markdown and DEMO_NOTE in r.markdown
