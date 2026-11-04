## JFK leads large-hub airports on international seat share in CY2025

International seat share is calculated as seats on international departing segments divided by all departing seats (T-100). For every airport in FAA hub class L, the value for 2025-01…2025-12 ranks as follows, highest first.

1. JFK 54.2%
2. MIA 44.9%
3. IAD 37.3%
4. EWR 32.4%
5. LAX 31.9%
6. SFO 29.9%
7. IAH 26.6%
8. BOS 21.9%
9. FLL 19.5%
10. ORD 17.2%
11. HNL 17.1%
12. DFW 15.1%
13. MCO 14.6%
14. SEA 13.8%
15. ATL 13.6%
16. PHL 13.5%
17. DTW 10.4%
18. MSP 10.1%
19. CLT 8.4%
20. TPA 7.4%
21. LAS 6.1%
22. DEN 6.0%
23. PHX 5.5%
24. SLC 4.9%
25. LGA 4.8%
26. AUS 4.7%
27. BWI 4.2%
28. SAN 4.1%
29. BNA 2.4%
30. DCA 1.7%

The share at JFK exceeds the share at MIA by 9.2% and exceeds the share at DCA by 52.5%. A separate minmax score within this set is 100 at JFK and 0 at DCA. No two airports have the same share, so the order has no ties. This is a descriptive rank of one calculated metric, not an investment screen and not a valuation.

**Findings and reasoning**
- *Fact*: In 2025-01…2025-12, calculated international seat share (calculated) among FAA large hubs ranks from JFK 54.2%, MIA 44.9%, IAD 37.3%, EWR 32.4%, LAX 31.9%, SFO 29.9%, IAH 26.6%, BOS 21.9%, FLL 19.5%, ORD 17.2%, HNL 17.1%, DFW 15.1%, MCO 14.6%, SEA 13.8%, ATL 13.6%, PHL 13.5%, DTW 10.4%, MSP 10.1%, CLT 8.4%, TPA 7.4%, LAS 6.1%, DEN 6.0%, PHX 5.5%, SLC 4.9%, LGA 4.8%, AUS 4.7%, BWI 4.2%, SAN 4.1%, BNA 2.4%, to DCA 1.7%. [F16, F21, F14, F11, F18, F28, F15, F4, F12, F23, F13, F9, F20, F27, F1, F24, F10, F22, F6, F30, F17, F8, F25, F29, F19, F2, F5, F26, F3, F7]
- *Fact*: The difference in international seat share is 9.2% between JFK and MIA and 52.5% between JFK and DCA. Both differences are calculated from the shares above. [F64, F63, F16, F21, F7]
- *Fact*: No two of these international seat shares are identical, so the rank has no ties. The minmax rank score inside this set is 100 at JFK and 0 at DCA. [F16, F21, F14, F11, F18, F28, F15, F4, F12, F23, F13, F9, F20, F27, F1, F24, F10, F22, F6, F30, F17, F8, F25, F29, F19, F2, F5, F26, F3, F7, F31, F60]
- *Fact*: Exploratory reads, not catalog metrics, put the FAA hub-class year at 2,025 (exploratory query) and the class-L airport count at 30 (exploratory query). Class-L airports with passenger seats in CY2025 number 30 (exploratory query), and months with those seats run from 12 (exploratory query) to 12 (exploratory query). [F61, F62, F67, F65, F66]
- *Inference*: Because the exploratory month counts run from 12 (exploratory query) to 12 (exploratory query), the CY2025 shares are not compared across airports that lack months of passenger seats. That does not show that each month contributes equally to the annual share. [F65, F66, F16]
- *Hypothesis (not established by the data)*: Airports toward the top of this list may hold that position because of airline network role and international air-service rights. The ranking does not establish unmet demand, a terminal-capacity constraint, or an investment return. [F16, F21, F7]

**Assumptions**
- The phrase large hub did not resolve to a city, airport, or region. It is bound to the catalog group filter hub class L, the FAA large-hub code.
- Higher international seat share ranks higher. The accompanying score is a minmax rescaling inside this airport set. It is not the seat share itself.
- The share uses the catalog formula for 2025-01…2025-12: seats on international departing T-100 segments divided by all departing seats.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F16 | International seat share — JFK — 2025-01…2025-12 | 54.2% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F21 | International seat share — MIA — 2025-01…2025-12 | 44.9% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F14 | International seat share — IAD — 2025-01…2025-12 | 37.3% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F11 | International seat share — EWR — 2025-01…2025-12 | 32.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F18 | International seat share — LAX — 2025-01…2025-12 | 31.9% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F28 | International seat share — SFO — 2025-01…2025-12 | 29.9% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F15 | International seat share — IAH — 2025-01…2025-12 | 26.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F4 | International seat share — BOS — 2025-01…2025-12 | 21.9% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F12 | International seat share — FLL — 2025-01…2025-12 | 19.5% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F23 | International seat share — ORD — 2025-01…2025-12 | 17.2% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F13 | International seat share — HNL — 2025-01…2025-12 | 17.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F9 | International seat share — DFW — 2025-01…2025-12 | 15.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F20 | International seat share — MCO — 2025-01…2025-12 | 14.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F27 | International seat share — SEA — 2025-01…2025-12 | 13.8% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F1 | International seat share — ATL — 2025-01…2025-12 | 13.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F24 | International seat share — PHL — 2025-01…2025-12 | 13.5% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F10 | International seat share — DTW — 2025-01…2025-12 | 10.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F22 | International seat share — MSP — 2025-01…2025-12 | 10.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F6 | International seat share — CLT — 2025-01…2025-12 | 8.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F30 | International seat share — TPA — 2025-01…2025-12 | 7.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F17 | International seat share — LAS — 2025-01…2025-12 | 6.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F8 | International seat share — DEN — 2025-01…2025-12 | 6.0% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F25 | International seat share — PHX — 2025-01…2025-12 | 5.5% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F29 | International seat share — SLC — 2025-01…2025-12 | 4.9% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F19 | International seat share — LGA — 2025-01…2025-12 | 4.8% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F2 | International seat share — AUS — 2025-01…2025-12 | 4.7% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F5 | International seat share — BWI — 2025-01…2025-12 | 4.2% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F26 | International seat share — SAN — 2025-01…2025-12 | 4.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F3 | International seat share — BNA — 2025-01…2025-12 | 2.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F7 | International seat share — DCA — 2025-01…2025-12 | 1.7% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F64 | difference(F16, F21) | 9.2% | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F63 | difference(F16, F7) | 52.5% | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F31 | Ranking score — JFK | 100 | calculated | see inputs | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F60 | Ranking score — DCA | 0 | calculated | see inputs | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F61 | faa_hub_class_cy (exploratory query) | 2,025 (exploratory query) | exploratory | as queried |  |  |
| F62 | n_airports (exploratory query) | 30 (exploratory query) | exploratory | as queried |  |  |
| F67 | n_with_seats (exploratory query) | 30 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F65 | min_months (exploratory query) | 12 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F66 | max_months (exploratory query) | 12 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |

**Methodology**
- `intl_seat_share`: Σ seats on international segments / Σ seats
- `derived:difference`: difference of [International seat share — JFK — 2025-01…2025-12] , [International seat share — MIA — 2025-01…2025-12]
- `rank_score`: Σ weight × minmax_in_set-scaled criterion; criteria: intl_seat_share (higher_better, w=1.0)
- `exploratory_sql`: column faa_hub_class_cy of: SELECT faa_hub_class_cy, count(*) AS n_airports FROM dim_airport_faa WHERE faa_hub_class = 'L' GROUP BY faa_hub_class_cy

**Caveats and limitations**
- Scores are relative to the airports in this set; adding/removing airports changes them.
- Exploratory SQL: definitions are not catalog metrics; verify before relying on it.
- Unmet demand, terminal capacity, fares, and profitability are not measured. A higher international seat share is not evidence of any of those.
- Only departing segments enter the metric. Arriving international seats are outside it.
- This is not an investment screen, so screen scenario flags were not produced. There are no ties in the seat share. Rank scores are relative to this set and would change if airports were added or removed.
- Hub-class year, class count, and month counts are exploratory SQL, not catalog metrics. Causes of a high or low share are not identified.