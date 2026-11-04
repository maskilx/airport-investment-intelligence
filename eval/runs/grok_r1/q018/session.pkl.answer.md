## Dominant-carrier seat share and departure delay are not established as associated across Mountain primary airports

Across FAA primary airports in the Census Mountain division, largest operating-carrier seat share and average departure delay were compared airport by airport for 2025-09…2026-07. The calculated Pearson correlation is 0.082. The calculated Spearman rank correlation is 0.163. Both point estimates are positive. The bootstrap interval for the Spearman correlation runs from -0.134 to 0.432 and uses 49 airports that have both values. That interval includes negative and positive values, so the sign of the rank association is not established. These figures are calculated associations across airports. They are not a forecast, and they do not show that carrier concentration causes delay.

**Findings and reasoning**
- *Fact*: Over 2025-09…2026-07, the calculated Pearson correlation between largest operating-carrier seat share and average departure delay is 0.082, and the calculated Spearman rank correlation is 0.163. Both point estimates are positive. [F113, F114, F19, F76]
- *Fact*: The bootstrap interval for the Spearman correlation runs from -0.134 to 0.432. The correlation uses 49 airports with both values. [F115, F116, F117]
- *Inference*: Because the Spearman interval includes both a negative value and a positive value, these data do not establish whether higher dominant-carrier seat share goes with higher or lower average departure delay across this set. [F114, F115, F116]

**Assumptions**
- Mountain division is the US Census Mountain division.
- Primary airports are those with FAA hub class L, M, S, or N, covering large, medium, small, and nonhub primary airports.
- Dominant carrier seat share is the largest operating carrier share of departing passenger and combi seats.
- The window is 2025-09…2026-07, the months inside both T-100 coverage, which runs through July 2026, and On-Time coverage, which starts in September 2025. A shared T12 window is not available.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F19 | Largest operating carrier's seat share — DEN — 2025-09…2026-07 | 40.5% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F113 | Pearson correlation: top_carrier_share vs avg_dep_delay_min | 0.082 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F114 | Spearman rank correlation: top_carrier_share vs avg_dep_delay_min | 0.163 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F115 | Spearman ρ 95% bootstrap CI, lower: top_carrier_share vs avg_dep_delay_min | -0.134 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F116 | Spearman ρ 95% bootstrap CI, upper: top_carrier_share vs avg_dep_delay_min | 0.432 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F117 | airports used: top_carrier_share vs avg_dep_delay_min | 49 airports | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F76 | Average departure delay — DEN — 2025-09…2026-07 | 16.0 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 93% (2025-09…2026-07) |
| F2 | Largest operating carrier's seat share — ABQ — 2025-09…2026-07 | 53.3% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F4 | Largest operating carrier's seat share — ASE — 2025-09…2026-07 | 99.8% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F5 | Largest operating carrier's seat share — AZA — 2025-09…2026-07 | 87.4% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F7 | Largest operating carrier's seat share — BIL — 2025-09…2026-07 | 19.6% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F9 | Largest operating carrier's seat share — BOI — 2025-09…2026-07 | 25.4% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F10 | Largest operating carrier's seat share — BTM — 2025-09…2026-07 | 99.3% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |

**Methodology**
- `top_carrier_share`: max over operating carriers of seat share, departing passenger/combi segments
- `pearson_r`: Pearson correlation of [top_carrier_share] and [avg_dep_delay_min] across airports
- `spearman_rho`: Spearman rank correlation of [top_carrier_share] and [avg_dep_delay_min] across airports
- `spearman_ci_low`: Spearman ρ 95% bootstrap CI, lower of [top_carrier_share] and [avg_dep_delay_min] across airports
- `spearman_ci_high`: Spearman ρ 95% bootstrap CI, upper of [top_carrier_share] and [avg_dep_delay_min] across airports
- `n`: airports used of [top_carrier_share] and [avg_dep_delay_min] across airports
- `avg_dep_delay_min`: Σ departure delay minutes (early = 0) / operated departures

**Caveats and limitations**
- T-100 carriers are operating carriers; regional affiliates appear separately from their mainline partner.
- Association across airports, not causation; confounders (size, hub status, region) are not controlled.
- n = 49 airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ.
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- The result is a cross-sectional association. It does not control for airport size, hub role, seasonality, or weather, and it is not evidence that carrier concentration causes delay.
- Average departure delay uses domestic flights of reporting carriers only. Early departures contribute zero minutes rather than negative minutes. International flights and non-reporting carriers are outside this metric.
- Seat share counts operating carriers separately, so regional affiliates are not rolled up to a mainline brand. Branded dominance can look lower than a passenger would perceive.
- Primary airports that lack a seat-share value or an On-Time average departure delay in this window are omitted. The number included is 49 airports.
- Unmet demand, terminal capacity, fares, and profitability are not measured by these series.
- The correlations are calculated values, not observed totals and not FAA forecasts.