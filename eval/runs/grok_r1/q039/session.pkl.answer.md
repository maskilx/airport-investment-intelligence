## SFO leads the equal-weights screen of primary hubs

The equal_weights expansion screen covers airports stored as FAA hub class L, M, or S. The result is a screening rank of expansion opportunity, not a valuation. SFO 78.36 is ordered first. The next scores are BNA 77.62, JAC 76.93, BZN 75.73, and ORD 75.60. The screen marks BNA, JAC, BZN, and ORD as tied with the airport ranked immediately above. The score gap from SFO 78.36 down to ORD 75.60 is 2.76. AUS 70.90 is the next airport. The screen does not mark AUS as tied with ORD, and the score gap from ORD 75.60 down to AUS 70.90 is 4.69.

The top quartile of scored airports is the equal_weights order from SFO through SLC 54.70. PHX 54.63 is the next airport. The screen marks PHX as tied with SLC, and the score gap from SLC 54.70 down to PHX 54.63 is 0.07.

Seat factor in that set over 2025-08…2026-07 is P10 76.4%, P25 77.9%, P50 80.3%, P75 81.4%, and P90 82.1%. The interquartile range is 3.5%. The span from P10 to P90 is 5.7%. Each airport counts equally.

The share of SFO operating hours above its verified instrument capacity rate is 0.2%. The screen flags SFO for instrument-condition headroom rather than a binding airfield constraint. Carrier-concentration flags in the top-quartile set, over 2025-08…2026-07, are BNA 58.4%, EWR 60.6%, MIA 56.4%, IAD 51.8%, SJC 61.3%, OAK 78.1%, IAH 59.1%, DFW 66.0%, and SLC 55.9%. The SNA row carries a regulatory-cap flag for a verified passenger cap and commercial arrival and departure curfews. Concentration and the cap sit beside the rank. They are not inputs to the score.

**Findings and reasoning**
- *Fact*: SFO 78.36 is ordered first on the equal_weights expansion screen of this primary-hub set. The next score is BNA 77.62. [F1573, F1575]
- *Fact*: The following scores are JAC 76.93, BZN 75.73, and ORD 75.60. The screen marks BNA, JAC, BZN, and ORD as tied with the airport ranked immediately above. The score gap from SFO 78.36 down to ORD 75.60 is 2.76. [F1575, F1576, F1577, F1578, F1573, F1760]
- *Fact*: AUS 70.90 is the next score after ORD 75.60. The screen does not mark AUS as tied with ORD. The score gap from ORD 75.60 down to AUS 70.90 is 4.69. [F1579, F1578, F1759]
- *Fact*: SLC 54.70 ranks immediately ahead of PHX 54.63 on the equal_weights screen. The screen marks PHX as tied with SLC. The score gap from SLC 54.70 down to PHX 54.63 is 0.07. [F1609, F1610, F1758]
- *Fact*: Over 2025-08…2026-07, seat factor in the top-quartile set is P10 76.4%, P25 77.9%, P50 80.3%, P75 81.4%, and P90 82.1%. The interquartile range is 3.5%. The span from P10 to P90 is 5.7%. [F1751, F1752, F1753, F1754, F1755, F1756, F1757]
- *Fact*: The share of SFO operating hours above its verified instrument capacity rate is 0.2%. The screen flags SFO for instrument-condition headroom rather than a binding airfield constraint. [F1574]
- *Fact*: Carrier-concentration flags in the top-quartile set over 2025-08…2026-07 are BNA 58.4%, EWR 60.6%, MIA 56.4%, IAD 51.8%, SJC 61.3%, OAK 78.1%, IAH 59.1%, DFW 66.0%, and SLC 55.9%. [F1161, F1188, F1235, F1206, F1278, F1242, F1207, F1182, F1279]
- *Fact*: The SNA row of this screen includes a regulatory-cap flag for a verified passenger cap and commercial arrival and departure curfews. [F1592]
- *Inference*: The seat-factor percentiles describe airport-level seat factor inside the equal_weights top quartile ending at SLC 54.70. Each airport counts equally, so a small hub and a large hub have the same weight. These calculated ratios do not measure unmet demand, terminal capacity, fares, or profitability. [F1751, F1753, F1756, F1609]

**Assumptions**
- Primary hubs means airports whose stored FAA hub class is L, M, or S: large, medium, and small hubs. Nonhub primary airports, hub class N, are excluded. The phrase did not resolve to a named place, so the analysis uses this hub-class group.
- Hub class is the class stored on the airport record. It is not recomputed from enplanements inside this screen.
- The top quartile is every scored airport with an equal_weights score at or above the upper quartile of the scored scores, using linear interpolation. That set is the screen order from SFO through SLC. SLC is on the cut and is included. PHX is the next airport and is below the cut. Airports the screen did not score are outside the set.
- Seat factor is the catalog metric on the T12 window 2025-08…2026-07. Each airport is weighted equally, not by passengers or by seats.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1573 | Expansion screen score — SFO (equal_weights) | 78.36 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1575 | Expansion screen score — BNA (equal_weights) | 77.62 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1576 | Expansion screen score — JAC (equal_weights) | 76.93 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1577 | Expansion screen score — BZN (equal_weights) | 75.73 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1578 | Expansion screen score — ORD (equal_weights) | 75.60 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1760 | difference(F1573, F1578) | 2.76 | calculated | see inputs | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1579 | Expansion screen score — AUS (equal_weights) | 70.90 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1759 | difference(F1578, F1579) | 4.69 | calculated | see inputs | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1609 | Expansion screen score — SLC (equal_weights) | 54.70 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1610 | Expansion screen score — PHX (equal_weights) | 54.63 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1758 | difference(F1609, F1610) | 0.07 | calculated | see inputs | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1751 | P10 of seat_factor across set | 76.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1752 | P25 of seat_factor across set | 77.9% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1753 | P50 of seat_factor across set | 80.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1754 | P75 of seat_factor across set | 81.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1755 | P90 of seat_factor across set | 82.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1756 | difference(F1754, F1752) | 3.5% | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1757 | difference(F1755, F1751) | 5.7% | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1574 | Share of operating hours with reporting-carrier schedule > IMC rate — SFO | 0.2% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; curated_constraints [current] |  |
| F1161 | Largest operating carrier's seat share — BNA — 2025-08…2026-07 | 58.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1188 | Largest operating carrier's seat share — EWR — 2025-08…2026-07 | 60.6% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1235 | Largest operating carrier's seat share — MIA — 2025-08…2026-07 | 56.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1206 | Largest operating carrier's seat share — IAD — 2025-08…2026-07 | 51.8% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1278 | Largest operating carrier's seat share — SJC — 2025-08…2026-07 | 61.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1242 | Largest operating carrier's seat share — OAK — 2025-08…2026-07 | 78.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1207 | Largest operating carrier's seat share — IAH — 2025-08…2026-07 | 59.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1182 | Largest operating carrier's seat share — DFW — 2025-08…2026-07 | 66.0% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1279 | Largest operating carrier's seat share — SLC — 2025-08…2026-07 | 55.9% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1592 | Expansion screen score — SNA (equal_weights) | 60.58 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F544 | FAA TAF enplanements change — SFO — FY2035 vs FY2025 | 8.46M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F976 | Enplaned passengers change (%) — SFO — 2025-08…2026-07 vs 2024-08…2025-07 | 0.6% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1135 | Home-CBSA per-capita income — SFO — CY2024 | $136,552 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F312 | FAA TAF enplanements change — BNA — FY2035 vs FY2025 | 3.74M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F744 | Enplaned passengers change (%) — BNA — 2025-08…2026-07 vs 2024-08…2025-07 | 7.8% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1020 | Home-CBSA per-capita income — BNA — CY2024 | $84,977 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F418 | FAA TAF enplanements change — JAC — FY2035 vs FY2025 | 152,766 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F850 | Enplaned passengers change (%) — JAC — 2025-08…2026-07 vs 2024-08…2025-07 | 8.7% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1072 | Home-CBSA per-capita income — JAC — CY2024 | $368,428 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F326 | FAA TAF enplanements change — BZN — FY2035 vs FY2025 | 430,057 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F758 | Enplaned passengers change (%) — BZN — 2025-08…2026-07 vs 2024-08…2025-07 | 9.5% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1027 | Home-CBSA per-capita income — BZN — CY2024 | $94,573 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F486 | FAA TAF enplanements change — ORD — FY2035 vs FY2025 | 11.44M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F918 | Enplaned passengers change (%) — ORD — 2025-08…2026-07 vs 2024-08…2025-07 | 5.9% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1106 | Home-CBSA per-capita income — ORD — CY2024 | $79,997 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F300 | FAA TAF enplanements change — AUS — FY2035 vs FY2025 | 3.64M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F732 | Enplaned passengers change (%) — AUS — 2025-08…2026-07 vs 2024-08…2025-07 | 4.7% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1014 | Home-CBSA per-capita income — AUS — CY2024 | $85,549 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F552 | FAA TAF enplanements change — SLC — FY2035 vs FY2025 | 3.39M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F984 | Enplaned passengers change (%) — SLC — 2025-08…2026-07 vs 2024-08…2025-07 | 0.3% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1138 | Home-CBSA per-capita income — SLC — CY2024 | $73,879 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F498 | FAA TAF enplanements change — PHX — FY2035 vs FY2025 | 6.07M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F930 | Enplaned passengers change (%) — PHX — 2025-08…2026-07 vs 2024-08…2025-07 | -0.1% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1112 | Home-CBSA per-capita income — PHX — CY2024 | $70,055 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F1715 | Seat factor — ATW — 2025-08…2026-07 | 81.9% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1716 | Seat factor — AUS — 2025-08…2026-07 | 76.5% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1717 | Seat factor — AVL — 2025-08…2026-07 | 81.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1718 | Seat factor — BNA — 2025-08…2026-07 | 76.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1719 | Seat factor — BOS — 2025-08…2026-07 | 81.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F1720 | Seat factor — BZN — 2025-08…2026-07 | 80.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F556 | FAA TAF enplanements change — SNA — FY2035 vs FY2025 | 1.06M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F988 | Enplaned passengers change (%) — SNA — 2025-08…2026-07 vs 2024-08…2025-07 | 2.6% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F1140 | Home-CBSA per-capita income — SNA — CY2024 | $86,376 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |

**Methodology**
- `screen_score:1.0`: Σ weight × anchored score of: Projected passenger increase (FAA TAF FY2025→FY2035, absolute) [10000→10000000, log10] w=0.3334; Realized passenger growth (T-100, trailing 12 months vs prior 12) [-0.05→0.1, linear] w=0.3333; Home-CBSA per-capita income (latest BEA year) [45000→110000, linear] w=0.3333
- `derived:difference`: difference of [Expansion screen score — SFO (equal_weights)] , [Expansion screen score — ORD (equal_weights)]
- `quantile:seat_factor`: 10th percentile (linear interpolation) across 36 airports
- `hours_above_imc_rate`: hours (date × local hour, ≥1 operated flight) where scheduled arr+dep of reporting carriers > 78 ops/h (highest verified IMC rate); lower bound on total demand
- `top_carrier_share`: max over operating carriers of seat share, departing passenger/combi segments
- `abs_change:taf_enplanements`: change of [FAA Terminal Area Forecast total enplanements (domestic + international)]: FY2035 vs FY2025
- `pct_change:passengers`: change (%) of [Σ passengers on departing passenger/combi segments]: 2025-08…2026-07 vs 2024-08…2025-07
- `cbsa_per_capita_income`: BEA personal income / population of the home CBSA
- `seat_factor`: Σ passengers / Σ seats, departing passenger/combi segments

**Caveats and limitations**
- Screening rank of expansion opportunity, not a financial valuation: no costs, debt, airline-agreement economics or construction risk are modelled.
- TAF component is an FAA forecast (unconstrained).
- Lower bound: excludes international, non-reporting and GA traffic.
- Capacity rate: FAA Airport Capacity Profile (verified), 78 ops/h.
- T-100 carriers are operating carriers; regional affiliates appear separately from their mainline partner.
- FAA TAF values for forecast years are FAA's unconstrained forecast, not observations.
- Federal fiscal year (Oct–Sep).
- T-100 passengers are segment enplanements (connecting passengers count at each enplanement).
- Home CBSA is an administrative proxy for the market area, not a measured catchment.
- Area-level value (home CBSA/county): airports or groups sharing an area repeat the same value; never add these across rows.
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- SJU, GUM, and STT are in the hub-class group and were not scored because home-CBSA per-capita income is missing. They have no screen rank and they are not in the seat-factor distribution.
- No airport in the hub-class group was listed below the screen enplanement gate.
- The screen marks long stretches of adjacent airports as tied, including the opening cluster through ORD and the boundary between SLC and PHX. A tie means the gap is inside the model tie band. The displayed order is still the score sort. The quartile set follows the percentile cut and does not expand along the whole tie chain.
- Scored airports other than SFO are flagged AIRFIELD_UNKNOWN because no verified capacity rate is on file. No scored airport is flagged as airfield-binding. The SNA passenger cap and curfews are screen flags, not catalog metrics, so the cap levels are not reported here as findings.
- This order is the equal_weights scenario. The same screen also returns base, demand_only, and momentum_heavy orders, and those orders differ.
- The score does not measure costs, debt, airline-agreement economics, construction risk, unmet demand, terminal capacity, fares, or profitability. Its passenger-increase input is an unconstrained FAA forecast. Seat factor is passengers divided by seats on departing passenger and combi segments. It is not a capacity residual.