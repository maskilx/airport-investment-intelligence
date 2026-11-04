"""Entity resolution: free text / codes / groups -> airport_id sets, with explicit ambiguity.

Policy (deterministic):
  * an exact airport code (current or historical, IATA/FAA) wins;
  * otherwise name/city matches among US airports with commercial traffic, ranked by enplanements;
    if two or more candidates are within 10x of each other in size the term is AMBIGUOUS
    (the caller decides: ask, or for contrast questions bind the most specific match);
  * region terms (state, Census division/region, CBSA/CSA title) resolve to groups, never to one airport;
  * group filters return members plus the members EXCLUDED by thresholds (never silently dropped).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .evidence import AmbiguousEntity, InvalidSpec, UnknownEntity

GROUP_KEYS = ("state", "census_division", "census_region", "hub_class", "cbsa", "csa", "min_enplanements",
              "towered", "airports")


@dataclass
class Resolution:
    term: str
    kind: str                                  # airport | group | ambiguous | unknown
    airport_ids: list[int] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"term": self.term, "kind": self.kind, "airport_ids": self.airport_ids,
                "candidates": self.candidates[:8], "note": self.note}


class Resolver:
    def __init__(self, con):
        self.con = con
        con.execute("""CREATE TEMP TABLE IF NOT EXISTS _res AS
            WITH enp AS (SELECT airport_id, enplanements FROM v_faa_enplanements_annual
                         WHERE cy = (SELECT max(cy) FROM v_faa_enplanements_annual)),
                 pax AS (SELECT origin_airport_id AS airport_id, sum(passengers) p FROM v_t100_segment
                         WHERE year = (SELECT max(year) - 1 FROM v_t100_segment) GROUP BY 1)
            SELECT d.airport_id, d.current_code AS code, d.all_codes, d.faa_lid, d.icao, d.name, d.city_name,
                   d.state_abr AS state, s.state_name, d.census_division, d.census_region, d.country,
                   f.faa_hub_class AS hub_class, x.cbsa_title AS cbsa, x.csa_title AS csa,
                   coalesce(enp.enplanements, pax.p, 0) AS size,
                   d.airport_id IN (SELECT airport_id FROM v_atads_airport_ops) AS towered
            FROM dim_airport d LEFT JOIN dim_airport_faa f USING (airport_id)
            LEFT JOIN xref_airport_county x USING (airport_id)
            LEFT JOIN ref_us_state s ON s.state_abr = d.state_abr
            LEFT JOIN enp USING (airport_id) LEFT JOIN pax USING (airport_id)""")
        cols = [c[0] for c in con.execute("DESCRIBE _res").fetchall()]
        self.rows = [dict(zip(cols, r)) for r in con.execute("SELECT * FROM _res").fetchall()]
        self.by_id = {r["airport_id"]: r for r in self.rows}
        import tomllib
        from airport_data.config import REPO_ROOT
        p = REPO_ROOT / "config" / "entity_aliases.toml"
        self.aliases = tomllib.loads(p.read_text()).get("alias", {}) if p.exists() else {}

    def describe(self, aid: int) -> dict[str, Any]:
        r = self.by_id[aid]
        return {"airport_id": aid, "code": r["code"], "name": r["name"], "city": r["city_name"], "state": r["state"],
                "hub_class": r["hub_class"], "cbsa": r["cbsa"], "enplanements_latest_cy": r["size"]}

    # ------------------------------------------------------------ single terms
    def resolve_term(self, term: str) -> Resolution:
        t = term.strip()
        if not t:
            return Resolution(term, "unknown", note="empty term")
        up = t.upper()
        al = self.aliases.get(t.lower())
        if al:
            if al["kind"] == "airport":
                aid = next(r["airport_id"] for r in self.rows if r["code"] == al["code"])
                return Resolution(term, "airport", [aid], [self.describe(aid)], al["note"])
            g = self.group({**dict(al["group"]), "min_enplanements": 10000})
            return Resolution(term, "group", g["airport_ids"], [{"kind": "group", "group": al["group"]}], al["note"])
        exact = [r for r in self.rows if up == r["code"] or up in (r["all_codes"] or []) or up == r["faa_lid"]
                 or up == r["icao"]]
        exact_us = [r for r in exact if r["country"] == "US"] or exact
        region = self._region(t)
        if len(exact_us) == 1 and not (region and len(up) == 2):
            r = exact_us[0]
            hist = up != r["code"]
            return Resolution(term, "airport", [r["airport_id"]], [self.describe(r["airport_id"])],
                              f"code {up} is a historical/alternate code for {r['code']}" if hist else "")
        cands = []
        if region:
            cands.append({"kind": "group", **region})
        lo = t.lower()
        name_hits = [r for r in self.rows if r["country"] == "US" and r["size"] and r["size"] >= 10000 and
                     (lo == (r["city_name"] or "").split(",")[0].strip().lower() or
                      (len(lo) >= 3 and (re.search(rf"\b{re.escape(lo)}\b", (r["name"] or "").lower())
                                         or re.search(rf"\b{re.escape(lo)}\b", (r["city_name"] or "").lower()))))]
        name_hits.sort(key=lambda r: -(r["size"] or 0))
        cands += [{"kind": "airport", **self.describe(r["airport_id"])} for r in name_hits[:8]]
        if len(exact_us) > 1:
            cands = [{"kind": "airport", **self.describe(r["airport_id"])} for r in exact_us] + cands
        if not cands:
            return Resolution(term, "unknown", note="no airport, city or region matches")
        if len(cands) == 1 and cands[0]["kind"] == "group":
            return Resolution(term, "group", cands[0]["airport_ids"], cands, cands[0]["note"])
        airports = [c for c in cands if c["kind"] == "airport"]
        exact_city = [c for c in airports if lo == (c["city"] or "").split(",")[0].strip().lower()]
        pool = exact_city or airports
        if region and region.get("exact") and not exact_city:      # "Texas", "New England": the region, not "East Texas Regional"
            return Resolution(term, "group", region["airport_ids"], cands, region["note"])

        def dominant(lst):
            return len(lst) == 1 or (lst[0]["enplanements_latest_cy"] or 0) >= 10 * (lst[1]["enplanements_latest_cy"] or 1)
        if exact_city and pool:   # a larger airport of the same metro just outside the city string -> ambiguous (Dallas: DAL vs DFW)
            rivals = [c for c in airports if c not in pool and c.get("cbsa") and c.get("cbsa") == pool[0].get("cbsa")
                      and (c["enplanements_latest_cy"] or 0) > (pool[0]["enplanements_latest_cy"] or 0)]
            if rivals:
                return Resolution(term, "ambiguous", [], rivals + pool, "the city name matches a smaller airport while a "
                                  "larger airport serves the same metro; ask or state the assumption")
        if pool and dominant(pool):
            others = [c.get("code") or c.get("group") for c in cands if c is not pool[0]]
            note = "exact city match" if exact_city else "dominant match by size"
            return Resolution(term, "airport", [pool[0]["airport_id"]], cands,
                              note + (f"; other candidates: {others[:6]}" if others else ""))
        if not airports and region:
            return Resolution(term, "group", region["airport_ids"], cands, region["note"])
        return Resolution(term, "ambiguous", [], cands, "several plausible matches; ask or state the assumption")

    def _region(self, t: str) -> dict[str, Any] | None:
        lo = t.lower().strip()
        for key, label in (("state_name", "state"), ("state", "state"), ("census_division", "census_division"),
                           ("census_region", "census_region"), ("cbsa", "cbsa"), ("csa", "csa")):
            hits = {r[key] for r in self.rows if r[key] and (str(r[key]).lower() == lo or
                                                              (key in ("cbsa", "csa") and len(lo) > 3 and lo in str(r[key]).lower()))}
            if len(hits) == 1:
                val = hits.pop()
                if key == "state_name":
                    val = next(r["state"] for r in self.rows if r["state_name"] == val)
                ids = self.group({label: val, "min_enplanements": 10000})["airport_ids"]
                return {"group": {label: val}, "airport_ids": ids, "exact": key not in ("cbsa", "csa") or str(val).lower() == lo,
                        "note": f"{label} '{val}': {len(ids)} airports with ≥10,000 enplanements"}
        return None

    # ------------------------------------------------------------ groups
    def group(self, spec: dict[str, Any]) -> dict[str, Any]:
        bad = set(spec) - set(GROUP_KEYS)
        if bad:
            raise InvalidSpec(f"unknown group filter(s) {sorted(bad)}", allowed=list(GROUP_KEYS))
        members, excluded = [], []
        min_enp = spec.get("min_enplanements")
        for r in self.rows:
            if r["country"] != "US":
                continue
            ok = True
            for k in ("state", "census_division", "census_region", "hub_class", "cbsa", "csa"):
                if k in spec:
                    want = spec[k] if isinstance(spec[k], list) else [spec[k]]
                    ok &= r[k] in want
            if "towered" in spec:
                ok &= bool(r["towered"]) == bool(spec["towered"])
            if "airports" in spec:
                ok &= r["airport_id"] in self.ids_for(spec["airports"])
            if not ok:
                continue
            if min_enp is not None and (r["size"] or 0) < float(min_enp):
                if (r["size"] or 0) > 0:
                    excluded.append({"code": r["code"], "enplanements_latest_cy": r["size"], "reason": f"< {min_enp:,} enplanements"})
                continue
            members.append(r["airport_id"])
        members.sort(key=lambda a: -(self.by_id[a]["size"] or 0))
        return {"airport_ids": members, "excluded": sorted(excluded, key=lambda e: -e["enplanements_latest_cy"])[:30],
                "n_excluded": len(excluded)}

    def ids_for(self, terms: list[Any], strict: bool = True) -> list[int]:
        out = []
        for t in terms:
            if isinstance(t, int):
                if t not in self.by_id:
                    raise UnknownEntity(f"unknown airport_id {t}")
                out.append(t)
                continue
            res = self.resolve_term(str(t))
            if res.kind == "airport":
                out += res.airport_ids
            elif res.kind == "ambiguous" and strict:
                raise AmbiguousEntity(f"'{t}' is ambiguous", candidates=res.candidates[:6])
            elif res.kind == "group":
                raise InvalidSpec(f"'{t}' is a region, not an airport; use entities.group", resolution=res.to_dict())
            else:
                raise UnknownEntity(f"'{t}' did not match any airport", term=t)
        return list(dict.fromkeys(out))

    def entities(self, ent: dict[str, Any]) -> tuple[list[int], dict[str, Any]]:
        """Spec 'entities' -> (airport_ids, resolution notes)."""
        if not isinstance(ent, dict) or not ent:
            raise InvalidSpec("entities must be {'airports': [...]} or {'group': {...}}")
        if "airports" in ent:
            ids = self.ids_for(ent["airports"])
            return ids, {"airports": [self.describe(a) for a in ids]}
        if "group" in ent:
            g = self.group(ent["group"])
            if not g["airport_ids"]:
                raise UnknownEntity("group matched no airports", group=ent["group"])
            return g["airport_ids"], {"group": ent["group"], "n_members": len(g["airport_ids"]),
                                      "members": [self.by_id[a]["code"] for a in g["airport_ids"][:60]],
                                      "excluded_by_threshold": g["excluded"], "n_excluded": g["n_excluded"]}
        raise InvalidSpec("entities must contain 'airports' or 'group'")

    def code(self, aid: int) -> str:
        return self.by_id[aid]["code"] if aid in self.by_id else str(aid)
