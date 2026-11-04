"""OfflineBackend: a deterministic, rule-based planner that speaks the same tool protocol as an LLM.

Purpose: run and demo the whole product (API, UI, memory, charts, evidence) with zero model calls and zero cost, and
exercise the runtime end-to-end in tests. It is NOT an LLM and is clearly labelled as such in every answer: it understands
a fixed set of question intents (screening, congestion comparison, long-haul share, unmet-demand indicators, trends,
named metrics) plus follow-ups that refer to entities in the conversation memory. Everything else gets an honest
"needs the LLM backend" reply. All numbers still come from the engine and pass the same grounding validator.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from airport_analytics.claims import is_assessment_question
from airport_analytics.information import check as check_information
from airport_analytics.information import match_concepts

from .models import ModelResponse, Usage

LABEL = "Offline demo planner (rule-based, no LLM)"
STOP = {"What", "Which", "Who", "How", "Why", "When", "Where", "Compare", "Show", "Tell", "Give", "List", "Rank", "Is",
        "Are", "Does", "Do", "Did", "Can", "Could", "And", "The", "A", "An", "In", "Of", "For", "At", "Out", "From", "Me",
        "Please", "Actually", "Also", "Now", "Then", "Same", "That", "Those", "It", "Its", "Their", "Them", "What's",
        "I", "We", "Let", "Okay", "Ok", "Yes", "No", "Thanks", "Airport", "Airports", "US", "FAA", "BTS", "TAF", "T12",
        "Terminal", "Expansion", "Congestion", "Unmet", "Demand", "Flights", "Long", "Haul", "Versus", "Vs", "Between",
        "Instead", "Meant", "Mean", "Use", "Look", "Trend", "Over", "Time", "Monthly"}
US_STATES = None
INTENT_WORDS = [
    ("screen", r"\b(expan|candidate|invest|opportunit|screen|modern|best airports?|strong)\w*"),
    ("congestion", r"\b(congest|crowd|busy|busier|delay|capacity constrain|peak)\w*"),
    ("long_haul", r"\blong[- ]?haul\b"),
    ("unmet", r"\b(unmet|pent[- ]up|latent|suppressed) demand\b|\bunmet\b"),
    ("trend", r"\b(trend|over time|monthly|month by month|series)\b"),
]
METRIC_WORDS = [
    ("seat_factor", r"seat factor|load factor"), ("passengers", r"passenger|enplanement|traffic|boarding"),
    ("seats", r"\bseats\b"), ("departures", r"departures"), ("dep_delay15_rate", r"delay rate|delays?\b"),
    ("cancel_rate", r"cancel"), ("avg_taxi_out_min", r"taxi"), ("intl_seat_share", r"international"),
    ("top_carrier_share", r"carrier concentration|dominant carrier|market share"),
    ("tower_operations", r"operations|movements"), ("grants_awarded_usd", r"grant|\baip\b"),
    ("npias_need_usd", r"npias|capital need|development need"), ("taf_enplanements", r"forecast"),
    ("freight_lbs", r"freight|cargo"), ("avg_stage_length", r"stage length|distance"),
]
NOT_IN_DATA = [   # topics the internal datasets do not measure -> say so instead of answering a nearby metric
    (r"\b(air)?fares?\b|ticket price|yield", "airfares", "passenger volumes, seat capacity and seat factors"),
    (r"\bgates?\b|square f(ee|oo)t|sq\.? ?ft|terminal (size|area|capacity)", "terminal gates or floor area",
     "scheduled peak-hour operations, passengers and FAA forecasts"),
    (r"cost per enplan|\bcpe\b|landing fees?|\brevenue|\bprofit|\bebitda|\bconcession|\bparking", "airport finances "
     "(CPE, fees, revenues)", "FAA grants awarded and NPIAS development needs"),
    (r"\bwind\b|precipitation|cloud ceiling|visibility|\bweather conditions?\b|temperature", "weather observations",
     "weather-attributed delay minutes from the On-Time data"),
    (r"security (wait|line)|\btsa wait|queue time", "security wait times", "passenger volumes and peak-hour schedules"),
]
THRESHOLD = re.compile(r"\b(\d{3,5})\s*-?\s*(?:mi\b|miles?\b)", re.I)
BOUND_LH = re.compile(r"\b(A\d+): [^;\n]*\[binds long_haul_share\.min_miles = (\d+)\]")
LIVE = re.compile(r"\b(right now|now|currently|today|at the moment|live)\b", re.I)
CORRECTION = re.compile(r"\b(actually|i meant|instead|not .* but|rather|correction|i mean)\b", re.I)
REFERENCE = re.compile(r"\b(that|this|those|these|same|it|its|them|their|earlier|previous|before|first one|second one|"
                       r"the airport|the other)\b", re.I)


def _nice(key: str) -> str:
    """Readable, digit-free name for a table column key such as 'dep_delay15_rate' or 'long_haul_share(min_miles=…)'."""
    return re.sub(r"\s+", " ", re.sub(r"\d+", "", key.split("(")[0].split(":")[-1]).replace("_", " ")).strip()


def _blocks(m) -> list[dict]:
    return m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]


def _tu(name: str, inp: dict) -> dict:
    return {"type": "tool_use", "id": "off_" + uuid.uuid4().hex[:8], "name": name, "input": inp}


def _text(t: str) -> ModelResponse:
    return ModelResponse([{"type": "text", "text": t}], "end_turn", Usage(requests=1), "offline")


def _calls(blocks: list[dict]) -> ModelResponse:
    return ModelResponse(blocks, "tool_use", Usage(requests=1), "offline")


class OfflineBackend:
    name = "offline"

    # ------------------------------------------------------------------ protocol
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> ModelResponse:
        qi = max(i for i, m in enumerate(messages) if m["role"] == "user" and any(
            b.get("type") == "text" and not b["text"].startswith("System:") for b in _blocks(m)))
        raw = next(b["text"] for b in reversed(_blocks(messages[qi])) if b.get("type") == "text")
        memory, q = (raw.split("## Current question\n", 1) if "## Current question\n" in raw else ("", raw))
        done = self._done(messages[qi:])
        prev = [b["text"] for m in messages[:qi] if m["role"] == "user" for b in _blocks(m)
                if b.get("type") == "text" and not b["text"].startswith(("System:", "["))]
        return self._plan(q.strip(), memory, done, prev[-1].split("## Current question\n")[-1] if prev else "")

    @staticmethod
    def _done(msgs: list[dict]) -> list[tuple[dict, Any]]:
        uses, out = {}, []
        for m in msgs:
            for b in _blocks(m):
                if b.get("type") == "tool_use":
                    uses[b["id"]] = b
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    try:
                        res = json.loads(b["content"])
                    except (ValueError, TypeError):
                        res = b.get("content")
                    out.append((uses[b["tool_use_id"]], res))
        return out

    # ------------------------------------------------------------------ planning
    def _plan(self, q: str, memory: str, done: list, prev_q: str = "") -> ModelResponse:
        intent = next((k for k, rx in INTENT_WORDS if re.search(rx, q, re.I)), None)
        q_intent = intent                  # what the question itself says (before context fills gaps)
        if not intent and CORRECTION.search(q) and prev_q:          # a correction keeps the previous question's intent
            intent = next((k for k, rx in INTENT_WORDS if re.search(rx, prev_q, re.I)), None)
        metrics = [m for m, rx in METRIC_WORDS if re.search(rx, q, re.I)]
        gap = next((g for g in match_concepts(q) if g != "unmet_demand"), None)
        if gap and intent not in ("screen", "long_haul", "unmet"):
            intent = "gap"                 # a measure we do not hold: classify it and run the proxies (not a refusal)
        focus_t = [(c, int(f), int(l)) for c, f, l in
                   re.findall(r"\b([A-Z][A-Z0-9]{2,3}) \(airport, first turn (\d+), last turn (\d+)\)", memory)]
        focus = [c for c, _, _ in focus_t]                      # most recent first
        ranked_codes = re.findall(r"\b([A-Z][A-Z0-9]{2,3}) \[F\d+\]", memory)
        if re.search(r"\b(first|earliest|originally)\b", q, re.I) and focus_t and not re.search(r"\bfirst (one|airport|candidate|ranked)\b", q, re.I):
            comparing = bool(re.search(r"\b(compare|versus|vs|against|with)\b", q, re.I) and REFERENCE.search(q))
            pool = [x for x in focus_t if not (comparing and x[0] == focus[0])] or focus_t
            # earliest turn; ties (several airports from one answer) -> best-ranked, then listing order
            earliest = min(enumerate(pool), key=lambda ix: (ix[1][1], ranked_codes.index(ix[1][0]) if ix[1][0] in ranked_codes
                                                            else 99, ix[0]))[1][0]
            focus = list(dict.fromkeys([focus[0], earliest])) if comparing else [earliest] + [c for c in focus if c != earliest]
        groups = re.findall(r"(\{[^{}]*\}) \(group", memory)
        prev_metrics = re.findall(r"Metrics used: ([^\n]+)", memory)
        prev_metrics = [m.strip() for m in prev_metrics[0].split(",")] if prev_metrics else []
        terms = self._terms(q)
        names = [u["name"] for u, _ in done]

        # 0) a measure we do not hold, and no airport to run proxies for: explain the gap and the useful next step
        if intent == "gap" and not done and not terms and not focus:
            info = check_information(q)
            return _text(f"[{LABEL}] {info['label'].capitalize()} is not in the internal datasets. "
                         f"What cannot be established: {info['cannot_establish']} Closest indicators I can compute: "
                         f"{', '.join(p['name'] for p in info['proxies'])}. Most useful next step: {info['next_step']} "
                         "Name an airport and I will run those indicators, labelled as proxies.")
        # 0b) an analyst-set long-haul threshold is a *bound* assumption: code then marks findings computed with any
        #     other threshold stale (assumptions.py), so a later answer cannot silently cite them
        bound = BOUND_LH.findall(memory)
        thr = THRESHOLD.search(q)
        if thr and intent == "long_haul" and "update_memory" not in names and \
                (not bound or int(bound[-1][1]) != int(thr.group(1))):
            upd = {"action": "set_assumption", "text": "Long-haul threshold set by the analyst (segment distance)",
                   "binds": {"metric": "long_haul_share", "param": "min_miles", "value": int(thr.group(1))}}
            if bound:
                upd["replaces"] = bound[-1][0]
            calls = [_tu("update_memory", upd)]
            if terms and "resolve_entities" not in names:
                calls.insert(0, _tu("resolve_entities", {"terms": terms}))
            return _calls(calls)
        # 1) resolve named places (and record a correction as an assumption)
        if terms and "resolve_entities" not in names:
            calls = [_tu("resolve_entities", {"terms": terms})]
            if CORRECTION.search(q) and not thr:
                from .memory import mask_numbers
                calls.append(_tu("update_memory", {"action": "set_assumption",
                                                    "text": "User correction: " + mask_numbers(q)[:200]}))
            return _calls(calls)
        airports, group, region_label = [], None, ""
        for u, res in done:
            if u["name"] != "resolve_entities" or not isinstance(res, dict):
                continue
            for r in res.get("resolutions", []):
                if r.get("kind") == "ambiguous":
                    opts = ", ".join(f"{c['code']} ({c.get('city', '')})" for c in r["candidates"] if c.get("code"))[:300]
                    return _text(f"“{r['term']}” matches more than one airport: {opts}. Which one do you mean?")
                if r.get("kind") == "unknown":
                    return _text(f"I could not find an airport, city or region called “{r['term']}” in the data. "
                                 "Could you give the airport code or the city and state?")
                if r.get("kind") == "airport":
                    c = next((c for c in r["candidates"] if c.get("airport_id") in r["airport_ids"] and c.get("code")), None)
                    if c:
                        airports.append(c["code"])
                elif r.get("kind") == "group":
                    g = next((c.get("group") for c in r["candidates"] if c.get("group")), None)
                    if g:
                        group, region_label = g, r["term"]
        # 2) references to earlier entities: ordinal references into the last ranked list first
        ranked = re.findall(r"Ordered result from turn \d+ \([^)]*\)+, best first: ([^\n]+)", memory)
        ordinals = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
        topn = re.search(r"\btop (two|three|four|five|\d)\b", q, re.I)
        nth = re.search(r"\b(first|second|third|fourth|fifth)\s+(one|airport|candidate|ranked)\b", q, re.I)
        ordinal_ref = False
        if not airports and not group and ranked and (topn or nth):
            ordinal_ref = True
            items = re.findall(r"\b([A-Z][A-Z0-9]{2,3})\b(?= \[|,|$)", ranked[-1])
            if topn:
                k = {"two": 2, "three": 3, "four": 4, "five": 5}.get(topn.group(1).lower()) or int(topn.group(1))
                airports = items[:k]
            else:
                airports = items[ordinals[nth.group(1).lower()]:][:1]
        assumed = None
        if is_assessment_question(q) and not airports and not group:
            # use the conversation before asking: the last ranked list, else the two airports in focus
            if ranked:
                airports = re.findall(r"\b([A-Z][A-Z0-9]{2,3})\b(?= \[|,|$)", ranked[-1])[:2]
            elif len(focus) >= 2:
                airports = focus[:2]
            if airports:
                assumed = f"the options are {' and '.join(airports)}, taken from the earlier conversation"
        if not airports and not group:
            if focus and (REFERENCE.search(q) or not terms):
                airports = focus[:2] if re.search(r"\b(both|compare|them|their|those|these)\b", q, re.I) else focus[:1]
            elif groups and intent == "screen":
                group = json.loads(groups[0])
        elif not ordinal_ref and REFERENCE.search(q) and focus and re.search(r"\b(compare|versus|vs|against|with)\b", q, re.I):
            airports = list(dict.fromkeys(airports + [c for c in focus if c not in airports][:1]))
        if not intent and not metrics and prev_metrics:
            metrics = [m for m in prev_metrics if m != "screen_score"][:4]
            if "screen_score" in prev_metrics and not metrics:
                intent = "screen"
        if not airports and not group:
            if intent == "screen":
                return _text("Which region or state should I screen for passenger growth opportunity (for example "
                             "New England, Texas or the Pacific division)?")
            return _text("Which airport or region should I analyze? You can use a code (SFO), a city, or a region.")

        analyses = [(u, r) for u, r in done if u["name"] == "run_analysis"]
        if is_assessment_question(q) and len(airports) >= 2 and q_intent not in ("screen", "congestion"):
            ctx_obj = self._objective_from_context(prev_metrics)
            if ctx_obj:
                intent = ctx_obj
                assumed = ((assumed + "; ") if assumed else "") + (
                    "the objective is passenger growth opportunity, as in the earlier screen" if ctx_obj == "screen"
                    else "the objective is airside congestion, as in the earlier comparison")
        assess = is_assessment_question(q) and len(airports) >= 2 and not group
        if assess and intent not in ("screen", "congestion") and not analyses:
            # a judgment needs an objective: different objectives use different criteria and can flip the answer
            return _text(f"Better for what? For {', '.join(airports)} I can assess passenger growth opportunity "
                         "(investment / expansion screen) or airside congestion (delay, taxi-out, peak-hour pressure). "
                         "Which objective should the assessment use?")
        if not analyses:
            lh = int(thr.group(1)) if thr else (int(bound[-1][1]) if bound else None)
            if intent == "gap":
                metrics = [p["metric"] for p in check_information(q)["proxies"]]
            specs = self._specs(intent, metrics, airports, group, lh)
            if not specs:
                return _text(f"[{LABEL}] I can run screening, congestion, long-haul, unmet-demand indicators, trends and "
                             "named metrics offline. This question needs the LLM backend (set AIRPORT_MODEL=gemini).")
            calls = [_tu("run_analysis", {"spec": s}) for s in specs]
            if intent == "congestion" and LIVE.search(q) and airports:      # "now / today": add the live FAA status
                calls.append(_tu("live_airport_status", {"airports": airports}))
            return _calls(calls)
        composes = [(u, r) for u, r in done if u["name"] == "compose_answer"]
        if composes:      # our own compose failed validation -> never show numbers; explain
            errs = (composes[-1][1] or {}).get("errors", []) if isinstance(composes[-1][1], dict) else []
            return _text(f"[{LABEL}] The answer draft did not pass grounding validation"
                         f"{' (details in the trace)' if errs else ''}; please rephrase.")
        ans = self._compose(intent, q, analyses, airports, region_label)
        live = [r for u, r in done if u["name"] == "live_airport_status" and isinstance(r, dict) and r.get("id")]
        for lv in live[:1]:
            for line in [x for x in lv.get("lines", [])[1:] if x.split(":")[0] in airports][:4]:
                ans.setdefault("claims", []).append({"kind": "external", "source": lv["id"], "quote": line,
                                                     "text": f"Live FAA NAS Status for {line.split(':')[0]}"})
            ans.setdefault("limitations", []).append(
                "Live FAA status is current operational context from a public API, not part of the reproducible "
                "dataset, and it does not change the historical indicators above.")
        if assumed:
            ans.setdefault("assumptions", []).insert(0, f"Assumed from context (say so if wrong): {assumed}.")
        return _calls([_tu("compose_answer", {"answer": ans})])

    @staticmethod
    def _objective_from_context(prev_metrics: list[str]) -> str | None:
        if "screen_score" in prev_metrics:
            return "screen"
        if any(m in prev_metrics for m in ("dep_delay15_rate", "avg_taxi_out_min", "peak_hour_ops_p95")):
            return "congestion"
        return None

    @staticmethod
    def _terms(q: str) -> list[str]:
        out = []
        for m in re.finditer(r"\b([A-Z][A-Za-z.]*(?:[ -][A-Z][A-Za-z.]*)*)(?:,\s*([A-Z][A-Za-z]+(?: [A-Z][a-z]+)?))?", q):
            phrase = m.group(1)
            words = [w for w in phrase.split() if w not in STOP]
            if not words:
                continue
            p = " ".join(words)
            if m.group(2) and m.group(2) not in STOP:
                p += ", " + m.group(2)
            if len(p) >= 2 and p not in out:
                out.append(p)
        return out[:6]

    @staticmethod
    def _specs(intent, metrics, airports, group, long_haul_miles: int | None = None) -> list[dict]:
        ent = {"airports": airports} if airports else {"group": group}
        gb = ["airport"] if len(airports) > 1 or group else []
        if intent == "screen":
            return [{"op": "screen", "entities": ent if group else {"airports": airports}}]
        if intent == "congestion":
            return [{"op": "aggregate", "entities": ent, "group_by": gb,
                     "metrics": ["dep_delay15_rate", "avg_taxi_out_min", "peak_hour_ops_p95", "tower_operations",
                                 "nas_delay_min_per_arrival"]}]
        if intent == "long_haul" and long_haul_miles:        # analyst fixed the definition: no alternatives
            return [{"op": "aggregate", "entities": ent, "group_by": gb, "metrics": [
                {"id": "long_haul_share", "params": {"weight": "departures", "min_miles": long_haul_miles}},
                {"id": "long_haul_share", "params": {"weight": "passengers", "min_miles": long_haul_miles}},
                "intl_seat_share", "avg_stage_length"]}]
        if intent == "long_haul":
            return [{"op": "aggregate", "entities": ent, "group_by": gb, "metrics": [
                {"id": "long_haul_share", "params": {"weight": "departures"}},
                {"id": "long_haul_share", "params": {"weight": "passengers"}},
                {"id": "long_haul_share", "params": {"weight": "departures", "min_miles": 2400}},
                "intl_seat_share", "avg_stage_length"]}]
        if intent == "unmet":
            return [{"op": "aggregate", "entities": ent, "group_by": gb, "metrics": [
                "seat_factor", "tight_capacity_pax_share", "peak_hour_ops_p95", "dep_delay15_rate",
                {"id": "passengers", "transform": {"type": "pct_change"}}, "top_carrier_share"]},
                {"op": "forecast_vs_actual", "entities": ent, "options": {"quantity": "enplanements"}}]
        if intent == "trend":
            return [{"op": "trend", "entities": ent, "metrics": (metrics or ["passengers"])[:2]}]
        if metrics:
            return [{"op": "aggregate", "entities": ent, "group_by": gb, "metrics": metrics[:5]}]
        return []

    # ------------------------------------------------------------------ answer composition (placeholders only)
    def _compose(self, intent, q, analyses, airports, region) -> dict:
        ok = [(u, r) for u, r in analyses if isinstance(r, dict) and not r.get("error")]
        errs = [r for _, r in analyses if isinstance(r, dict) and r.get("error")]
        lim = [f"{LABEL}: answers follow fixed templates; use the LLM backend for open-ended reasoning."]
        for e in errs:
            lim.append(f"Not established: {e.get('error')} — " + re.sub(r"\d", "#", str(e.get("message", "")))[:200])
        if not ok:
            return {"headline": "This could not be established from the data",
                    "body": "The analyses needed for this question returned errors; see the limitations below.",
                    "limitations": lim}
        if intent == "gap":
            return self._compose_gap(q, ok, airports, lim)
        if is_assessment_question(q) and len(airports) >= 2 and not region and intent in ("screen", "congestion"):
            return self._compose_assessment(intent, ok, airports, lim)
        if intent == "screen":
            return self._compose_screen(ok[0][1], region, lim)
        cells = []                                # (airport, metric_key, fid)
        for _, r in ok:
            for row in r.get("table", []) if r.get("op") != "trend" else []:
                ap = row.get("airport") or (airports[0] if len(airports) == 1 else None)
                for k, v in row.items():
                    if isinstance(v, dict) and "id" in v:
                        cells.append((ap, k, v["id"]))
            if r.get("op") == "trend":
                for s in r.get("summary", []):
                    cells.append((s.get("airport"), "slope", s["slope_per_month"]["id"]))
        vals_by_id = {}
        for _, r_ in ok:
            for b in r_.get("findings", []) or []:
                vals_by_id[b["id"]] = b.get("value")
        missing = [f for _, _, f in cells if vals_by_id.get(f, 0) is None]
        cells = [x for x in cells if x[2] not in missing]
        by_ap: dict[str, list[str]] = {}
        for ap, _, fid in cells:
            by_ap.setdefault(ap or "the selected airports", []).append(fid)
        body = [f"- **{ap}**: " + "; ".join(f"{{{f}.name}} {{{f}}} ({{{f}.period}})" for f in fids[:8])
                for ap, fids in by_ap.items()]
        claims = [{"kind": "fact", "text": f"{ap}: {{{f}.name}} is {{{f}}} ({{{f}.period}}).", "support": [f]}
                  for ap, _, f in cells[:12] if ap]
        if missing:
            lim.append("Not established (the source has no qualifying records for this airport and window, e.g. On-Time "
                       "covers only reporting carriers): " + "; ".join(f"{{{f}.label}}" for f in missing[:8]) + ".")
        charts = []
        if len(by_ap) > 1:
            metric_keys = list(dict.fromkeys(k for _, k, _ in cells))
            for mk in metric_keys[:3]:
                fids = [f for _, k, f in cells if k == mk]
                vals = {}
                for _, row_r in ok:
                    for row in row_r.get("table", []):
                        if isinstance(row.get(mk), dict):
                            vals[row.get("airport")] = (row[mk]["id"], row[mk].get("value"))
                if len(fids) > 1:
                    charts.append({"type": "bar", "title": "", "findings": fids})
                    num = sorted(((v, f) for f, v in vals.values() if isinstance(v, (int, float))), key=lambda x: -x[0])
                    if len(num) > 1:
                        # a typed comparison: code checks compatibility + direction and writes the sentence
                        from airport_analytics.claims import SIMILAR_REL_TOL
                        tie = abs(num[0][0] - num[1][0]) <= SIMILAR_REL_TOL * max(abs(num[0][0]), abs(num[1][0]), 1e-12)
                        if len(num) == 2:
                            rel = "similar" if tie else "higher"
                        else:
                            rel = None if tie else "highest"
                        if rel:
                            claims.append({"kind": "comparison", "relation": rel, "findings": [f for _, f in num]})
        trend = [r for _, r in ok if r.get("op") == "trend"]
        if trend and trend[0].get("table"):
            fids = [v["id"] for row in trend[0]["table"] for k, v in row.items() if isinstance(v, dict) and "id" in v]
            charts.append({"type": "line", "title": "Monthly series", "findings": fids})
        head = {"congestion": "Congestion indicators", "long_haul": "Long-haul share of departures",
                "unmet": "Demand-pressure indicators", "trend": "Trend"}.get(intent, "Requested metrics")
        ans = {"headline": f"{head}: {', '.join(a for a in by_ap if a)}", "body": "\n\n".join(body), "claims": claims,
               "assumptions": [], "limitations": lim, "charts": charts}
        if intent == "congestion" and cells:
            ans["claims"].append({"kind": "inference", "support": [f for _, _, f in cells][:10], "text":
                                  "These are airside indicators: they show how busy and how punctual the airfield "
                                  "operation is, not how crowded the passenger terminal is."})
        periods = sorted({p for p in re.findall(r"\{(F\d+)\.period\}", " ".join(body))})
        if intent == "congestion" and periods:
            ans["assumptions"].append("Each indicator compares the airports over the same window. Windows differ between "
                                      "sources (each value shows its own), as each source publishes on its own schedule.")
        if intent == "congestion":
            ans["assumptions"].append("Congestion is read from airside indicators (delay rate, taxi-out, scheduled "
                                      "peak hour, tower operations); terminal/landside congestion is not in the data.")
        if intent == "long_haul":
            ans["assumptions"].append("Long-haul is defined by segment distance; the question leaves the definition "
                                      "open, so alternative thresholds and weights are shown unless the analyst sets a threshold.")
        if intent == "unmet":
            ind = [f for _, k, f in cells if k.split("(")[0] in ("seat_factor", "tight_capacity_pax_share",
                                                                  "peak_hour_ops_p95", "dep_delay15_rate")]
            ans["claims"].append({"kind": "hypothesis", "text": "High seat factors, a large share of passengers on "
                                  "capacity-tight routes and a busy scheduled peak are consistent with demand exceeding "
                                  "supply, but unmet demand itself is not observed in this data.", "support": ind[:8],
                                  "alternatives": [
                                      "airlines may run high load factors by network and pricing choice, not because "
                                      "seats are scarce",
                                      "peak-hour pressure may reflect schedule banking (hub waves) rather than "
                                      "demand that cannot be served",
                                      "airfield, slot or gate-allocation rules may limit supply independently of "
                                      "terminal size"]})
            ans["limitations"].append("Unmet demand is not directly measurable here (no fares, spill or booking data).")
            info = check_information("unmet demand")
            ans["investigation"] = {
                "objective": "Understand whether demand at the airport exceeds what is served, and why",
                "question_type": "investigation",
                "investigated": ["whether unmet demand is measured in the internal datasets (it is not)",
                                 "demand-pressure indicators: load factor, capacity-tight routes, peak scheduling, "
                                 "delays, traffic change, carrier concentration, forecast versus actual"],
                "established": [f"{{{f}.name}} at {ap}: {{{f}}} ({{{f}.period}})" for ap, k, f in cells
                                if k.split("(")[0] in ("seat_factor", "tight_capacity_pax_share", "peak_hour_ops_p95")][:3],
                "unknown": [info["cannot_establish"], "which of the competing explanations dominates"],
                "next_step": info["next_step"]}
        return ans

    @staticmethod
    def _compose_gap(q: str, ok: list, airports: list[str], lim: list[str]) -> dict:
        """The requested measure is not held: show the proxies (labelled), what they cannot establish, the next step."""
        info = check_information(q)
        facts, est = [], []
        for _, r in ok:
            for row in r.get("table", []):
                ap = row.get("airport") or (airports[0] if len(airports) == 1 else None)
                for k, v in row.items():
                    if isinstance(v, dict) and v.get("id") and v.get("value") is not None and ap:
                        facts.append({"kind": "fact", "text": f"Proxy, {ap}: {{{v['id']}.name}} is {{{v['id']}}} "
                                      f"({{{v['id']}.period}}).", "support": [v["id"]]})
                        est.append(f"{{{v['id']}.name}} at {ap}: {{{v['id']}}}")
        lim.append(f"{info['label'].capitalize()} is not in the internal datasets, so the values above are proxies, not "
                   f"measurements of it, and this is not established: {info['cannot_establish'].rstrip('.')}.")
        return {"headline": "What the data can and cannot show: " + ", ".join(airports),
                "body": "The requested measure is not held in the internal datasets. Below are the closest indicators, "
                        "labelled as proxies, what they cannot establish, and the most useful next step.",
                "claims": facts[:10],
                "assumptions": [f"Proxy rationale: {info['proxy_note']}"] if info.get("proxy_note") else [],
                "limitations": lim,
                "investigation": {
                    "objective": f"Answer a question about {info['label']} for " + ", ".join(airports),
                    "question_type": "investigation",
                    "investigated": [f"whether the catalog measures {info['label']} (case: {info['case'].replace('_', ' ')})",
                                     "which catalog indicators are reasonable proxies"],
                    "established": est[:4],
                    "unknown": [info["cannot_establish"]] + [f"needed: {n}" for n in info["needed"][:2]],
                    "next_step": info["next_step"]}}

    @staticmethod
    def _compose_assessment(intent: str, ok: list, airports: list[str], lim: list[str]) -> dict:
        """Objective -> criteria tied to findings -> conditional judgment. Which option each criterion favours is
        computed (and re-checked by claims.py); the planner never invents values, weights or support."""
        from airport_analytics.claims import SIMILAR_REL_TOL

        def winner(pairs, higher_better=True):          # pairs [(airport, fid, value)] -> favoured airport or neither
            num = [p for p in pairs if isinstance(p[2], (int, float))]
            if len(num) < 2:
                return "neither"
            num.sort(key=lambda p: -p[2] if higher_better else p[2])
            a, b = num[0][2], num[1][2]
            return "neither" if abs(a - b) <= SIMILAR_REL_TOL * max(abs(a), abs(b), 1e-12) else num[0][0]
        crits, fids_all = [], []
        if intent == "screen":
            r = ok[0][1]
            rows = r.get("table", [])
            objective = ("Passenger growth opportunity (stage A screen): which airport combines stronger forecast growth, "
                         "realized growth and market income. Terminal need and project returns are not assessed.")
            names = {"incremental_enplanements": "Forecast passenger increase (FAA TAF)",
                     "realized_growth": "Realized passenger growth (T-100)", "market_income": "Market income (BEA)"}
            for comp, nm in names.items():
                pairs = [(row["airport"], row["components"][comp]["points_id"], row["components"][comp]["points"]) for row in rows]
                crits.append({"name": nm, "findings": [p[1] for p in pairs], "favors": winner(pairs),
                              "direction": "higher_is_better",
                              "why": "points contributed under the documented screen weighting"})
            pairs = [(row["airport"], row["score"]["id"], row["score"]["value"]) for row in rows]
            crits.append({"name": "Overall growth opportunity score", "findings": [p[1] for p in pairs],
                          "favors": winner(pairs), "direction": "higher_is_better",
                          "why": "sum of the weighted factor points"})
            top = rows[0]["airport"] if rows else None
            stable = bool(rows) and all(v == 1 for v in rows[0].get("scenario_ranks", {}).values())
            close = len(rows) > 1 and rows[1].get("tied_with_previous")
            unscored = [x["airport"] for x in (r.get("gate") or {}).get("below_scale", [])] + \
                [x["airport"] for x in r.get("not_scored", [])]
            if unscored:
                lim.append("Not scored (below the passenger-scale gate or missing an input): " + ", ".join(unscored) + ".")
            abstain = bool(close) or len(rows) < 2
            reason = ("the scores are within the tie band, so the airports are too close to call on this screen"
                      if close else "fewer than two airports could be scored")
            judgment = "" if abstain else (
                f"{top} is the stronger passenger-growth opportunity of the airports compared"
                + (", and it stays first under every weighting scenario." if stable
                   else " under the base weighting, but the order changes under other weightings, so treat it as conditional."))
            cond = ["the FAA forecast growth is realized",
                    "no binding airfield, regulatory or terminal constraint, which this screen does not establish"]
            change = ["dated terminal and airfield capacity records with primary evidence",
                      "committed or announced terminal projects at either airport",
                      "a different priority between forecast growth, momentum and market income"]
        else:
            r = ok[0][1]
            rows = r.get("table", [])
            objective = ("Lower airside congestion: which airport operates with less delay and less peak-hour pressure "
                         "(airside indicators; passenger-terminal crowding is not measured).")
            keys = [("dep_delay15_rate", "Departure delay rate"), ("avg_taxi_out_min", "Average taxi-out time"),
                    ("peak_hour_ops_p95", "Scheduled peak-hour operations"), ("nas_delay_min_per_arrival", "NAS delay per arrival")]
            for k, nm in keys:
                pairs = [(row.get("airport"), row[k]["id"], row[k].get("value")) for row in rows if isinstance(row.get(k), dict)]
                if len(pairs) >= 2 and all(isinstance(p[2], (int, float)) for p in pairs):
                    crits.append({"name": nm, "findings": [p[1] for p in pairs], "favors": winner(pairs, False),
                                  "direction": "lower_is_better", "why": "lower means less airside pressure"})
            votes = [c_["favors"] for c_ in crits if c_["favors"] != "neither"]
            best = max(set(votes), key=votes.count) if votes else None
            abstain = len(crits) < 2 or not best or votes.count(best) <= len(crits) / 2
            reason = ("the indicators point in different directions, with no majority"
                      if len(crits) >= 2 else "too few comparable indicators are available")
            judgment = "" if abstain else f"{best} shows less airside congestion on most of the indicators compared."
            cond = ["airside indicators are the relevant notion of congestion (terminal crowding is not measured)",
                    "On-Time coverage (reporting carriers, domestic flights) is representative at both airports"]
            change = ["terminal throughput or security-wait data", "the same indicators for international traffic",
                      "a longer or seasonal comparison window"]
        fids_all = [i for c_ in crits for i in c_["findings"]]
        favours: dict[str, list[str]] = {}
        for c_ in crits:
            if c_["favors"] != "neither" and not c_["name"].startswith("Overall"):
                favours.setdefault(c_["favors"], []).append(c_["name"].split(" (")[0].lower())
        tradeoffs = [f"{opt} is favoured on {', '.join(names)}" for opt, names in favours.items()] if len(favours) > 1 else []
        claim = {"kind": "assessment", "objective": objective, "criteria": crits, "judgment": judgment,
                 "abstain": abstain, "conditional_on": cond, "would_change": change, "tradeoffs": tradeoffs,
                 **({"abstain_reason": reason} if abstain else {})}
        head = ("Assessment: passenger growth opportunity, " if intent == "screen" else "Assessment: airside congestion, ") \
            + " and ".join(airports)
        return {"headline": head,
                "body": "The objective, the criteria with their evidence, and the judgment follow. Each criterion cites "
                        "the findings it rests on; which airport it favours is computed from those values.",
                "claims": [claim],
                "assumptions": ["The objective above is the interpretation used; a different objective would use "
                                "different criteria."],
                "limitations": lim,
                "charts": [{"type": "bar", "title": "", "findings": crits[-1]["findings"]}] if crits else []}

    @staticmethod
    def _compose_screen(r: dict, region: str, lim: list[str]) -> dict:
        rows = r.get("table", [])[:8]
        lines, claims, fids = [], [], []
        for row in rows:
            c = row["components"]
            flags = ", ".join(f["flag"] for f in row.get("flags", [])) or "none"
            tie = " (tied with the previous airport)" if row.get("tied_with_previous") else ""
            ci, cg, cm = c["incremental_enplanements"], c["realized_growth"], c["market_income"]
            lines.append(f"- **{row['airport']}**{tie}: score **{{{row['score']['id']}}}** = "
                         f"projected passenger increase {{{ci['points_id']}}} + realized growth {{{cg['points_id']}}} + "
                         f"market income {{{cm['points_id']}}}. Inputs: FAA TAF increase {{{ci['input']['id']}}}, "
                         f"T-100 growth {{{cg['input']['id']}}}, CBSA income per capita {{{cm['input']['id']}}}. "
                         f"Flags: {flags}.")
            fids.append(row["score"]["id"])
        if fids:      # rank, set size and robustness across weighting scenarios are written by code from findings
            claims.append({"kind": "ranking", "findings": fids[:3]})
        below = [b["airport"] for b in (r.get("gate") or {}).get("below_scale", [])]
        if below:
            lim.append("Below the passenger-scale gate and not scored: " + ", ".join(below) + ".")
        lim.append(r.get("disclaimer", ""))
        lim.append("Terminal suitability (whether a terminal is the binding constraint) and project economics are not "
                   "established by this screen; they need dated capacity, committed-project and cost evidence.")
        lim.append("Constraint flags use records in effect at the screen's as-of date (recorded with each score); expired "
                   "caps are excluded and records without primary or secondary evidence are flagged as unverified, not used.")
        return {"headline": f"Passenger growth opportunity screen{' in ' + region if region else ''}",
                "body": "Airports in rank order (base scenario). Each score is the sum of its weighted factor "
                        "contributions; the scoring method is listed below the answer.\n\n" + "\n".join(lines),
                "claims": claims,
                "assumptions": ["Screen weights and anchors are the documented base scenario (config/screening.toml); "
                                "a screening rank, not a valuation."],
                "limitations": [x for x in lim if x],
                "charts": [{"type": "bar", "title": "Passenger growth opportunity score (base scenario)", "findings": fids}]}
