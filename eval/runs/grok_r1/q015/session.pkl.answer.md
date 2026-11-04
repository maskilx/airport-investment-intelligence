## Scottsdale (SCF) general-aviation share of tower operations moved from 68.8% in October 2023 to 55.7% in September 2026

SDL is Scottsdale Airport, stored under the code SCF. General-aviation share of tower operations is (itinerant GA + local civil) / total tower operations. Each monthly figure is a calculated value from FAA ATADS over 2023-10…2026-09.

October 2023: 68.8%. November 2023: 64.3%. December 2023: 64.9%. January 2024: 61.2%. February 2024: 59.6%. March 2024: 60.2%. April 2024: 59.7%. May 2024: 61.6%. June 2024: 61.7%. July 2024: 61.4%. August 2024: 60.0%. September 2024: 61.3%. October 2024: 59.6%. November 2024: 58.2%. December 2024: 56.8%. January 2025: 57.6%. February 2025: 56.9%. March 2025: 56.6%. April 2025: 59.1%. May 2025: 60.3%. June 2025: 61.7%. July 2025: 65.7%. August 2025: 66.0%. September 2025: 67.7%. October 2025: 61.6%. November 2025: 59.1%. December 2025: 58.7%. January 2026: 57.4%. February 2026: 58.8%. March 2026: 57.0%. April 2026: 58.0%. May 2026: 58.1%. June 2026: 59.4%. July 2026: 61.3%. August 2026: 58.5%. September 2026: 55.7%.

The descriptive linear slope of this monthly series is -0.00 ratio per month. The year-over-year change for 2026-09 is -17.7%. The September 2026 share minus the October 2023 share is -13.1%.

**Findings and reasoning**
- *Fact*: Each listed month is the calculated general-aviation share of tower operations at SCF, defined as (itinerant GA + local civil) / total tower operations. [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20, F21, F22, F23, F24, F25, F26, F27, F28, F29, F30, F31, F32, F33, F34, F35, F36]
- *Fact*: The ordinary least-squares slope of the monthly series over 2023-10…2026-09 is -0.00 ratio per month. [F37]
- *Fact*: The year-over-year change for 2026-09 is -17.7%. [F38]
- *Fact*: The September 2026 share minus the October 2023 share is -13.1%. [F39, F36, F1]
- *Inference*: Read in order, the share is lower in December 2024 (56.8%) and March 2025 (56.6%) than in October 2023 (68.8%), higher in September 2025 (67.7%) than in March 2025, and lower in September 2026 (55.7%) than in September 2025. [F1, F15, F18, F24, F36, F38]
- *Inference*: Within this window, October 2023 is the highest monthly share and September 2026 is the lowest. [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20, F21, F22, F23, F24, F25, F26, F27, F28, F29, F30, F31, F32, F33, F34, F35, F36]

**Assumptions**
- SDL is bound to Scottsdale Airport in Phoenix, AZ, whose current code is SCF. The resolver describes SDL as a historical or alternate code for that single airport.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | General-aviation share of tower operations — month=2023-10 — 2023-10…2026-09 | 68.8% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F36 | General-aviation share of tower operations — month=2026-09 — 2023-10…2026-09 | 55.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F37 | Linear trend per month — ga_ops_share — SCF | -0.00 ratio per month | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F2 | General-aviation share of tower operations — month=2023-11 — 2023-10…2026-09 | 64.3% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F3 | General-aviation share of tower operations — month=2023-12 — 2023-10…2026-09 | 64.9% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F4 | General-aviation share of tower operations — month=2024-01 — 2023-10…2026-09 | 61.2% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F5 | General-aviation share of tower operations — month=2024-02 — 2023-10…2026-09 | 59.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F6 | General-aviation share of tower operations — month=2024-03 — 2023-10…2026-09 | 60.2% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F7 | General-aviation share of tower operations — month=2024-04 — 2023-10…2026-09 | 59.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F8 | General-aviation share of tower operations — month=2024-05 — 2023-10…2026-09 | 61.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F9 | General-aviation share of tower operations — month=2024-06 — 2023-10…2026-09 | 61.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F10 | General-aviation share of tower operations — month=2024-07 — 2023-10…2026-09 | 61.4% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F11 | General-aviation share of tower operations — month=2024-08 — 2023-10…2026-09 | 60.0% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F12 | General-aviation share of tower operations — month=2024-09 — 2023-10…2026-09 | 61.3% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F13 | General-aviation share of tower operations — month=2024-10 — 2023-10…2026-09 | 59.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F14 | General-aviation share of tower operations — month=2024-11 — 2023-10…2026-09 | 58.2% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F15 | General-aviation share of tower operations — month=2024-12 — 2023-10…2026-09 | 56.8% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F16 | General-aviation share of tower operations — month=2025-01 — 2023-10…2026-09 | 57.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F17 | General-aviation share of tower operations — month=2025-02 — 2023-10…2026-09 | 56.9% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F18 | General-aviation share of tower operations — month=2025-03 — 2023-10…2026-09 | 56.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F19 | General-aviation share of tower operations — month=2025-04 — 2023-10…2026-09 | 59.1% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F20 | General-aviation share of tower operations — month=2025-05 — 2023-10…2026-09 | 60.3% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F21 | General-aviation share of tower operations — month=2025-06 — 2023-10…2026-09 | 61.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F22 | General-aviation share of tower operations — month=2025-07 — 2023-10…2026-09 | 65.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F23 | General-aviation share of tower operations — month=2025-08 — 2023-10…2026-09 | 66.0% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F24 | General-aviation share of tower operations — month=2025-09 — 2023-10…2026-09 | 67.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F25 | General-aviation share of tower operations — month=2025-10 — 2023-10…2026-09 | 61.6% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F26 | General-aviation share of tower operations — month=2025-11 — 2023-10…2026-09 | 59.1% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F27 | General-aviation share of tower operations — month=2025-12 — 2023-10…2026-09 | 58.7% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F28 | General-aviation share of tower operations — month=2026-01 — 2023-10…2026-09 | 57.4% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F29 | General-aviation share of tower operations — month=2026-02 — 2023-10…2026-09 | 58.8% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F30 | General-aviation share of tower operations — month=2026-03 — 2023-10…2026-09 | 57.0% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F31 | General-aviation share of tower operations — month=2026-04 — 2023-10…2026-09 | 58.0% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F32 | General-aviation share of tower operations — month=2026-05 — 2023-10…2026-09 | 58.1% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F33 | General-aviation share of tower operations — month=2026-06 — 2023-10…2026-09 | 59.4% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F34 | General-aviation share of tower operations — month=2026-07 — 2023-10…2026-09 | 61.3% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F35 | General-aviation share of tower operations — month=2026-08 — 2023-10…2026-09 | 58.5% | calculated | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F38 | YoY change of last month — ga_ops_share — SCF | -17.7% | calculated | 2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)] |  |
| F39 | difference(F36, F1) | -13.1% | calculated | 2023-10…2026-09 | 2023-10…2026-09 | faa_atads_ops [2023-10…2026-09 (36 periods)]; faa_atads_ops [2023-10…2026-09 (36 periods)] |  |

**Methodology**
- `ga_ops_share`: (itinerant GA + local civil) / total tower operations
- `trend_slope:ga_ops_share`: OLS slope of monthly ga_ops_share, 2023-10…2026-09
- `yoy:ga_ops_share`: 2026-09 vs 2025-09
- `derived:difference`: difference of [General-aviation share of tower operations — month=2026-09 — 2023-10…2026-09] , [General-aviation share of tower operations — month=2023-10 — 2023-10…2026-09]

**Caveats and limitations**
- ATADS counts operations at towered airports during tower hours, all user classes.
- Monthly series include seasonality; slope is descriptive.
- ATADS counts operations at towered airports during tower hours and includes all user classes. Operations outside tower hours are not in this series.
- The share can move because general-aviation operations change, because other user classes change, or both. These results do not separate those drivers.
- Unmet demand, terminal capacity, fares, and profitability are not measured here.
- The linear slope includes seasonality and is descriptive only. It is not a seasonally adjusted trend and not a forecast.
- The figure -13.1% is the arithmetic difference of the two monthly shares. The figure -17.7% is the relative change for the last month versus the same month one year earlier. Neither figure is a valuation or a screening rank.