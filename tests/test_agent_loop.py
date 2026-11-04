"""Agent loop guarantees with a scripted backend (no LLM needed)."""
import pytest

from airport_data.config import get_paths

pytestmark = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")


def _agent(turns):
    from airport_agent.loop import Agent, ScriptedBackend
    return Agent(ScriptedBackend(turns))


def tu(i, name, inp):
    return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}


def test_grounded_answer_flow():
    a = _agent([
        [tu(1, "run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}}})],
        [tu(2, "compose_answer", {"answer": {"headline": "SFO seat factor", "body": "Seat factor was {F1} ({F1.period}).",
                                              "claims": [{"kind": "fact", "text": "{F1}", "support": ["F1"]}]}})],
    ])
    r = a.ask("What is SFO's seat factor?")
    assert r.kind == "answer" and "F1" in r.cited_findings and "**Evidence**" in r.markdown


def test_ungrounded_number_never_shown():
    a = _agent([[{"type": "text", "text": "SFO's seat factor is 82%."}]] * 4)
    r = a.ask("What is SFO's seat factor?")
    assert r.kind == "fallback" and "82" not in r.markdown


def test_clarification_without_numbers_is_allowed():
    a = _agent([[{"type": "text", "text": "Do you mean Portland, Oregon (PDX) or Portland, Maine (PWM)?"}]])
    r = a.ask("How busy is Portland?")
    assert r.kind == "clarification"


def test_rejected_answer_is_returned_to_model_then_fixed():
    a = _agent([
        [tu(1, "run_analysis", {"spec": {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["BOS"]}}})],
        [tu(2, "compose_answer", {"answer": {"headline": "BOS carried 21M", "body": "x"}})],     # literal number
        [tu(3, "compose_answer", {"answer": {"headline": "BOS traffic", "body": "{F1}"}})],
    ])
    r = a.ask("BOS passengers?")
    assert r.kind == "answer" and [c["error"] for c in r.tool_calls] == [None, "grounding_validation_failed", None]
