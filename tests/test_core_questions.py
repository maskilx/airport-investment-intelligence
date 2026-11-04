"""Regressions for the core questions: an answer must not silently answer a narrower
question (ANC cargo), must surface recorded restrictions (SNA cap and curfew, SFO runway records), and a lower-bound
measurement must never be reported as headroom. All offline: no model calls (scripted or rule-based backends)."""
import json

import pytest

from airport_agent.models import ScriptedBackend
from airport_agent.offline import OfflineBackend
from airport_agent.runtime import Agent
from airport_analytics.tools import Session, tool_schemas
from airport_data.config import get_paths

needs_db = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")


def _lh(agent, cited_only=True):
    return [f for f in agent.evidence.all() if f.metric_id.startswith("long_haul_share")]


@needs_db
def test_anc_long_haul_counts_all_flights_first_and_shows_the_cargo_split():
    a = Agent(OfflineBackend(), live_status=False)
    r = a.ask("What is the percentage of long haul flights out of Anchorage airport?")
    assert r.kind == "answer"
    by = {f.metric_id: f.value for f in _lh(a)}
    all_, pax, frt = (by[f"long_haul_share(min_miles=3000,scope={s},weight=departures)"]
                      for s in ("all", "passenger", "freight"))
    # ANC is a cargo hub: passenger-only would understate the share of long-haul *flights* several-fold
    assert pax < all_ < frt and all_ > 3 * pax
    first = r.structured["claims"][0]["text"] if r.structured.get("claims") else r.markdown
    assert "scope=all" in r.markdown.split("scope=passenger")[0]          # the all-flights value is listed first
    assert "all-cargo" in r.markdown and "passenger-terminal" in r.markdown
    assert first


@needs_db
def test_threshold_follow_up_keeps_all_scopes_and_stales_the_default():
    a = Agent(OfflineBackend(), live_status=False)
    a.ask("What is the percentage of long haul flights out of Anchorage airport?")
    r = a.ask("Use 2000 miles instead")
    assert r.kind == "answer"
    cited = [a.evidence.get(f) for f in r.cited_findings if f in {x.id for x in a.evidence.all()}]
    lh = [f for f in cited if f.metric_id.startswith("long_haul_share")]
    assert {"scope=all", "scope=passenger", "scope=freight"} <= {p for f in lh for p in f.metric_id.split(",")
                                                                 if p.startswith("scope=")}
    assert all("min_miles=2000" in f.metric_id for f in lh)
    assert all(f.status == "stale" for f in _lh(a) if "min_miles=2000" not in f.metric_id)


@needs_db
def test_lax_sna_congestion_surfaces_recorded_restrictions_with_evidence_level():
    a = Agent(OfflineBackend(), live_status=False)
    r = a.ask("Compare LA and Santa Ana airport congestion levels.")
    assert r.kind == "answer", r.markdown
    md = r.markdown
    assert "Recorded operating restrictions" in md and "Annual passenger limit (MAP)" in md and "Curfew" in md
    assert "checked only against a search snippet" in md          # the curfew records: never stated as verified fact
    hyp = [ln for ln in md.splitlines() if ln.startswith("- *Hypothesis") and "At SNA" in ln]
    assert hyp and "Competing explanations" in hyp[0] and "conditional limits" in hyp[0]


OCAIR = "https://www.ocair.com/about/administration/settlement-agreement/key-provisions-settlement-agreement/"


@needs_db
def test_sna_passenger_limit_cites_the_official_source_and_stays_conditional():
    """Both Phase 3 values appear only as verbatim official quotes WITH their condition, linked to ocair.com; the
    answer separates a regulatory limit from actual traffic and physical terminal capacity."""
    a = Agent(OfflineBackend(), live_status=False)
    r = a.ask("Compare LA and Santa Ana airport congestion levels.")
    md = r.markdown
    assert OCAIR in md and "newportbeachca.gov" not in md
    for line in [ln for ln in md.splitlines() if "12.2 MAP" in ln or "12.5 MAP" in ln]:
        assert "IF 11.21 MAP is" in line and "External source" in line and "conditional limit" in line
    assert "12.2 MAP" in md and "12.5 MAP" in md and "certain mitigation measures are met" in md
    assert "not the airport's actual traffic, not its physical terminal capacity" in md
    assert "which value applies is not established" in md
    ext = r.structured.get("external") or []
    assert any(e["url"] == OCAIR for e in ext)


@needs_db
def test_sfo_unmet_demand_lists_runway_and_capacity_records():
    a = Agent(OfflineBackend(), live_status=False)
    r = a.ask("What is the unmet flight demand in SFO airport and why?")
    assert r.kind == "answer"
    assert "runway geometry (verified, secondary source)" in r.markdown
    assert "capacity rates" in r.markdown and "verified, primary source" in r.markdown
    assert "not directly measurable" in r.markdown                 # still never a measured unmet-demand number


@needs_db
def test_constraints_tool_reports_effectiveness_and_evidence_and_rejects_empty_input():
    s = Session()
    res = s.call("airport_constraints", {"airports": ["sna", "XYZ"], "as_of": "2026-11-04"})
    caps = [r for r in res["records"] if r["category"] == "regulatory_cap"]
    assert {r["effective"] for r in caps} == {"ended", "in_effect"}            # Phase 2 ended 2025-12-31
    assert all(r["evidence"] == "primary" and r["source_url"] == OCAIR for r in caps)
    phase3 = [r for r in caps if "Phase 3" in r["item"]]
    assert len(phase3) == 2 and all(r["conditional"] and r["effective"] == "in_effect" for r in phase3)
    assert all(r["external_id"].startswith("W") and "IF 11.21 MAP" in r["evidence_quote"] for r in phase3)
    curfews = [r for r in res["records"] if r["category"] == "curfew"]
    assert curfews and all(r["evidence"] == "snippet" and not r["usable_as_fact"] and "external_id" not in r
                           for r in curfews)
    assert res["airports_without_records"] == ["XYZ"]
    assert s.call("airport_constraints", {"airports": []}).get("error")
    assert "airport_constraints" in {t["name"] for t in tool_schemas()}


@needs_db
def test_lower_bound_schedule_never_reports_airfield_headroom():
    s = Session()
    r = s.call("run_analysis", {"spec": {"op": "screen", "entities": {"airports": ["SFO", "LAX", "SNA"]}}})
    flags = [f for row in r["table"] for f in row["flags"]]
    assert not any("HEADROOM" in f["flag"] for f in flags)
    sfo = next(f for row in r["table"] if row["airport"] == "SFO" for f in row["flags"] if f["flag"].startswith("AIRFIELD"))
    assert sfo["flag"] in ("AIRFIELD_BINDING", "AIRFIELD_NOT_SHOWN_BINDING")
    if sfo["flag"] == "AIRFIELD_NOT_SHOWN_BINDING":
        assert sfo["class"] == "not_established"


@needs_db
def test_screen_is_reproducible_across_independent_sessions():
    spec = {"op": "screen", "entities": {"group": {"census_division": "New England"}}}
    out = []
    for _ in range(2):
        s = Session()
        r = s.call("run_analysis", {"spec": spec})
        if r.get("error"):                                           # group key spelled differently in this build
            r = s.call("run_analysis", {"spec": {"op": "screen", "entities": {"airports":
                       ["BOS", "PWM", "HVN", "BDL", "PVD", "MHT", "BTV"]}}})
        out.append([(row["airport"], row["rank"], row["score"]["value"]) for row in r["table"]])
    assert out[0] == out[1] and out[0][0][0] == "BOS"


@needs_db
def test_scripted_llm_can_use_constraints_then_compose_a_number_free_context_sentence():
    """Mocked model (no API): calls the new tool, writes context in words, cites only findings for numbers."""
    def tu(i, name, inp):
        return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}
    spec = {"op": "aggregate", "metrics": ["dep_delay15_rate"], "entities": {"airports": ["SNA"]}}
    ans = {"answer": {"headline": "SNA delay rate and recorded restrictions",
                      "body": "Delay rate {F1} ({F1.period}). A passenger cap and a curfew are reported (snippet evidence).",
                      "claims": [{"kind": "fact", "text": "{F1}", "support": ["F1"]}]}}
    bad = {"answer": {"headline": "SNA", "body": "SNA is capped at 12.2 million passengers.", "claims": []}}
    b = ScriptedBackend([[tu(1, "airport_constraints", {"airports": ["SNA"]}), tu(2, "run_analysis", {"spec": spec})],
                         [tu(3, "compose_answer", bad)], [tu(4, "compose_answer", ans)]])
    a = Agent(b, live_status=False)
    r = a.ask("Is SNA restricted?")
    assert r.kind == "answer" and "12.2" not in r.markdown
    first_result = json.loads(b.calls[1]["messages"][-1]["content"][0]["content"])
    assert first_result["records"] and "not findings" in first_result["note"]
    rejected = json.loads(b.calls[2]["messages"][-1]["content"][0]["content"])
    assert rejected["error"] == "grounding_validation_failed"


@needs_db
def test_roi_question_answers_the_measurable_part_and_says_roi_is_not_established():
    r = Agent(OfflineBackend(), live_status=False).ask("What is the ROI of expanding BOS?")
    assert r.kind == "answer" and "BOS" in r.markdown              # "ROI" is not mistaken for a place
    assert "profitability or investor returns" in r.markdown and "passenger growth opportunity only" in r.markdown
