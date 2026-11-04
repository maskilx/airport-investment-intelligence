## MIA has the longest CY2025 seat-weighted stage length of the four named Florida airports

For CY2025, seat-weighted average stage length on departing segments was 1,574 miles at Miami International (MIA), 1,160 miles at Orlando International (MCO), 1,068 miles at Fort Lauderdale Hollywood International (FLL), and 1,028 miles at Tampa International (TPA). Each value is calculated, defined as Σ(seats·distance) / Σ seats, and covers 2025-01…2025-12 from bts_t100_segment [2025-01…2025-12 (12 periods)].

MIA is the longest of the four. It is 414 miles longer than MCO (35.6% higher) and 546 miles longer than TPA (53.1% higher). MCO, FLL, and TPA sit much closer together: MCO is 92.28 miles longer than FLL, FLL is 39.74 miles longer than TPA, and the full span from MCO to TPA is 132 miles. The gap from MIA down to MCO is 3.132 times that MCO-to-TPA span.

**Findings and reasoning**
- *Fact*: In CY2025, seat-weighted average stage length was 1,574 miles at MIA, 1,160 miles at MCO, 1,068 miles at FLL, and 1,028 miles at TPA. These are calculated values for 2025-01…2025-12. [F1, F2, F3, F4]
- *Fact*: The order is MIA, then MCO, then FLL, then TPA. MIA exceeds MCO by 414 miles and TPA by 546 miles. MCO exceeds FLL by 92.28 miles, and FLL exceeds TPA by 39.74 miles. Relative to MCO, MIA is 35.6% higher; relative to TPA, MIA is 53.1% higher. The span from MCO to TPA is 132 miles. [F5, F6, F7, F8, F9, F10, F11]
- *Inference*: MIA is set apart from the other three named airports. The MIA-to-MCO gap (414 miles) is 3.132 times the entire span from MCO to TPA (132 miles), while the steps among MCO, FLL, and TPA are 92.28 miles and 39.74 miles. [F5, F6, F7, F9, F12]

**Assumptions**
- The comparison set is exactly the four airports named in the question. MIA resolved only to Miami International Airport, MCO only to Orlando International Airport, TPA only to Tampa International Airport, and FLL only to Fort Lauderdale Hollywood International Airport. Each is in Florida with FAA hub class L.
- Primary Florida airports is read as that named list. Other Florida commercial airports are outside this comparison.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F3 | Seat-weighted average stage length — MIA — 2025-01…2025-12 | 1,574 miles | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F2 | Seat-weighted average stage length — MCO — 2025-01…2025-12 | 1,160 miles | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F1 | Seat-weighted average stage length — FLL — 2025-01…2025-12 | 1,068 miles | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F4 | Seat-weighted average stage length — TPA — 2025-01…2025-12 | 1,028 miles | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F5 | difference(F3, F2) | 414 miles | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F10 | pct_difference(F3, F2) | 35.6% | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F8 | difference(F3, F4) | 546 miles | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F11 | pct_difference(F3, F4) | 53.1% | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F6 | difference(F2, F1) | 92.28 miles | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F7 | difference(F1, F4) | 39.74 miles | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F9 | difference(F2, F4) | 132 miles | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F12 | ratio(F5, F9) | 3.132 | calculated | 2025-01…2025-12 | 2025-01…2025-12 | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |

**Methodology**
- `avg_stage_length`: Σ(seats·distance) / Σ seats
- `derived:difference`: difference of [Seat-weighted average stage length — MIA — 2025-01…2025-12] , [Seat-weighted average stage length — MCO — 2025-01…2025-12]
- `derived:pct_difference`: pct_difference of [Seat-weighted average stage length — MIA — 2025-01…2025-12] , [Seat-weighted average stage length — MCO — 2025-01…2025-12]
- `derived:ratio`: ratio of [difference(F3, F2)] , [difference(F2, F4)]

**Caveats and limitations**
- The metric is seat-weighted average stage length on T-100 departing segments for all carriers, domestic and international. It is not passenger-weighted stage length, and it is not the catalog long-haul share.
- Unmet demand, terminal capacity, fares, and profitability are not measured by this comparison, and these data do not establish why the stage lengths differ.
- The figures are calculated from observed seats and distance for the full calendar year CY2025. They are not forecasts or estimates.