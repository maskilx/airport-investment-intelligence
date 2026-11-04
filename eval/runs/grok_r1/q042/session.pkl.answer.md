## FAA large_hub NAS delay is uneven, and the peak-hour association has no established sign

Over 2025-09…2026-08, calculated NAS delay minutes per arrival across FAA large_hub airports (hub class L) is 1.9 min at P10 of nas_delay_min_per_arrival across set, 2.5 min at P25 of nas_delay_min_per_arrival across set, 3.1 min at P50 of nas_delay_min_per_arrival across set, 5.0 min at P75 of nas_delay_min_per_arrival across set, and 7.7 min at P90 of nas_delay_min_per_arrival across set. These percentiles are calculated.

Ordered from the highest calculated NAS delay, SFO is 10.6 min with relative rank score 100, LGA is 8.3 min with relative rank score 74.69, EWR is 7.9 min with relative rank score 70.24, ORD is 7.7 min with relative rank score 68.82, and BOS is 7.2 min with relative rank score 63.12. SLC is the low end of the same ranking at 1.3 min. The relative scores 100, 74.69, 70.24, 68.82, and 63.12 are not equal, so that ordering has no tie. No large_hub airport was left unscored. This is a delay ranking inside the set, not an investment screen and not a valuation, so it has no screening flags.

Observed scheduled peak-hour operations at those high-delay airports are 66 operations/hour at SFO, 55 operations/hour at LGA, 46 operations/hour at EWR, 152 operations/hour at ORD, and 56 operations/hour at BOS. A correlation using only that high-delay slice cannot be estimated: the operator returned insufficient_data. Across the full large_hub set, the calculated Pearson correlation of NAS delay with scheduled peak-hour operations is 0.097 and the calculated Spearman rank correlation is 0.058. The Spearman bootstrap interval runs from -0.334 to 0.408 and uses 30 airports. The interval contains negative and positive values, so the sign of the rank association is not established. That association is calculated across airports. It is not a cause, not a forecast, and not evidence of unmet demand, terminal capacity, fares, or profitability.

Calculated On-Time coverage over 2025-09…2026-07 is 65.7% at EWR, 78.1% at SFO, 76.2% at LGA, 81.8% at ORD, and 74.9% at BOS. The partial-slice caveat applies to EWR 65.7%, IAD 45.9%, IAH 55.1%, JFK 48.4%, and MIA 57.7%. The delay and peak-hour window is 2025-09…2026-08.

**Findings and reasoning**
- *Fact*: Over 2025-09…2026-08, the calculated distribution of NAS delay minutes per arrival across the FAA large_hub set is 1.9 min (P10 of nas_delay_min_per_arrival across set), 2.5 min (P25 of nas_delay_min_per_arrival across set), 3.1 min (P50 of nas_delay_min_per_arrival across set), 5.0 min (P75 of nas_delay_min_per_arrival across set), and 7.7 min (P90 of nas_delay_min_per_arrival across set). [F31, F32, F33, F34, F35]
- *Fact*: SFO calculated NAS delay is 10.6 min and its relative rank score is 100. LGA calculated NAS delay is 8.3 min and its relative rank score is 74.69. EWR calculated NAS delay is 7.9 min and its relative rank score is 70.24. ORD calculated NAS delay is 7.7 min and its relative rank score is 68.82. BOS calculated NAS delay is 7.2 min and its relative rank score is 63.12. SLC calculated NAS delay, the low end of the same ranking, is 1.3 min. [F63, F66, F54, F67, F46, F68, F58, F69, F39, F70, F64]
- *Inference*: The relative scores for SFO, LGA, EWR, ORD, and BOS are not equal, so the high-delay ordering has no tie. The ranking is a within-set delay order, not an investment screen, and it produces no screening flags. [F66, F67, F68, F69, F70]
- *Fact*: Observed scheduled peak-hour operations are 66 operations/hour at SFO, 55 operations/hour at LGA, 46 operations/hour at EWR, 152 operations/hour at ORD, and 56 operations/hour at BOS. [F153, F144, F136, F148, F129]
- *Fact*: Across the full large_hub set, the calculated Pearson correlation of NAS delay with scheduled peak-hour operations is 0.097, the calculated Spearman rank correlation is 0.058, the Spearman bootstrap interval runs from -0.334 to 0.408, and the airports used are 30 airports. [F156, F157, F158, F159, F160]
- *Inference*: The Spearman interval contains both negative and positive values, so the sign of the rank association between NAS delay and scheduled peak-hour operations is not established. The result is an association across airports, not a cause. [F156, F157, F158, F159, F160]
- *Fact*: Calculated On-Time coverage over 2025-09…2026-07 is 65.7% at EWR, 78.1% at SFO, 76.2% at LGA, 81.8% at ORD, and 74.9% at BOS. [F181, F198, F189, F193, F174]
- *Fact*: The partial-slice coverage caveat is attached to EWR 65.7%, IAD 45.9%, IAH 55.1%, JFK 48.4%, and MIA 57.7%. [F181, F184, F185, F186, F191]
- *Inference*: EWR calculated NAS delay 7.9 min and observed peak-hour operations 46 operations/hour describe a partial On-Time slice, because EWR coverage 65.7% carries the partial-slice caveat. [F46, F136, F181]

**Assumptions**
- Large hubs are FAA hub class L, the large_hub set. resolve_entities returned unknown for the phrases large hubs, large hub, and large_hub, so the analysis uses the hub_class group filter.
- Worst means the highest calculated NAS delay minutes per arrival. The rank gives a higher delay a higher relative score, scaled within this set. Scores change if airports are added or removed.
- Peak hour ops means the catalog scheduled peak-hour metric (the percentile measure), not the single busiest scheduled hour.
- The reported correlation uses the full large_hub set over the same T12 window as the distribution. A correlation limited to the high-delay airports alone is not what was estimated.
- The window is the default T12, which resolved to 2025-09…2026-08 for NAS delay and for scheduled peak-hour operations.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F31 | P10 of nas_delay_min_per_arrival across set | 1.9 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F32 | P25 of nas_delay_min_per_arrival across set | 2.5 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F33 | P50 of nas_delay_min_per_arrival across set | 3.1 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F34 | P75 of nas_delay_min_per_arrival across set | 5.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F35 | P90 of nas_delay_min_per_arrival across set | 7.7 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F63 | NAS delay minutes per arrival — SFO — 2025-09…2026-08 | 10.6 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F66 | Ranking score — SFO | 100 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F54 | NAS delay minutes per arrival — LGA — 2025-09…2026-08 | 8.3 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 76% (2025-09…2026-07) |
| F67 | Ranking score — LGA | 74.69 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F46 | NAS delay minutes per arrival — EWR — 2025-09…2026-08 | 7.9 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 66% (2025-09…2026-07) |
| F68 | Ranking score — EWR | 70.24 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F58 | NAS delay minutes per arrival — ORD — 2025-09…2026-08 | 7.7 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 82% (2025-09…2026-07) |
| F69 | Ranking score — ORD | 68.82 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F39 | NAS delay minutes per arrival — BOS — 2025-09…2026-08 | 7.2 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 75% (2025-09…2026-07) |
| F70 | Ranking score — BOS | 63.12 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F64 | NAS delay minutes per arrival — SLC — 2025-09…2026-08 | 1.3 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 94% (2025-09…2026-07) |
| F153 | Scheduled peak hour (95th percentile) — SFO — 2025-09…2026-08 | 66 operations/hour | observed | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F144 | Scheduled peak hour (95th percentile) — LGA — 2025-09…2026-08 | 55 operations/hour | observed | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 76% (2025-09…2026-07) |
| F136 | Scheduled peak hour (95th percentile) — EWR — 2025-09…2026-08 | 46 operations/hour | observed | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 66% (2025-09…2026-07) |
| F148 | Scheduled peak hour (95th percentile) — ORD — 2025-09…2026-08 | 152 operations/hour | observed | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 82% (2025-09…2026-07) |
| F129 | Scheduled peak hour (95th percentile) — BOS — 2025-09…2026-08 | 56 operations/hour | observed | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 75% (2025-09…2026-07) |
| F156 | Pearson correlation: nas_delay_min_per_arrival vs peak_hour_ops_p95 | 0.097 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F157 | Spearman rank correlation: nas_delay_min_per_arrival vs peak_hour_ops_p95 | 0.058 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F158 | Spearman ρ 95% bootstrap CI, lower: nas_delay_min_per_arrival vs peak_hour_ops_p95 | -0.334 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F159 | Spearman ρ 95% bootstrap CI, upper: nas_delay_min_per_arrival vs peak_hour_ops_p95 | 0.408 | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F160 | airports used: nas_delay_min_per_arrival vs peak_hour_ops_p95 | 30 airports | calculated | see inputs | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F181 | On-Time coverage of airline departures — EWR — 2025-09…2026-07 | 65.7% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 66% (2025-09…2026-07) |
| F198 | On-Time coverage of airline departures — SFO — 2025-09…2026-07 | 78.1% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 78% (2025-09…2026-07) |
| F189 | On-Time coverage of airline departures — LGA — 2025-09…2026-07 | 76.2% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 76% (2025-09…2026-07) |
| F193 | On-Time coverage of airline departures — ORD — 2025-09…2026-07 | 81.8% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F174 | On-Time coverage of airline departures — BOS — 2025-09…2026-07 | 74.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 75% (2025-09…2026-07) |
| F184 | On-Time coverage of airline departures — IAD — 2025-09…2026-07 | 45.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 46% (2025-09…2026-07) |
| F185 | On-Time coverage of airline departures — IAH — 2025-09…2026-07 | 55.1% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 55% (2025-09…2026-07) |
| F186 | On-Time coverage of airline departures — JFK — 2025-09…2026-07 | 48.4% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 48% (2025-09…2026-07) |
| F191 | On-Time coverage of airline departures — MIA — 2025-09…2026-07 | 57.7% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 58% (2025-09…2026-07) |
| F1 | NAS delay minutes per arrival — ATL — 2025-09…2026-08 | 2.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 80% (2025-09…2026-07) |
| F2 | NAS delay minutes per arrival — AUS — 2025-09…2026-08 | 2.6 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 94% (2025-09…2026-07) |
| F3 | NAS delay minutes per arrival — BNA — 2025-09…2026-08 | 2.9 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 93% (2025-09…2026-07) |
| F4 | NAS delay minutes per arrival — BOS — 2025-09…2026-08 | 7.2 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 75% (2025-09…2026-07) |
| F5 | NAS delay minutes per arrival — BWI — 2025-09…2026-08 | 2.3 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 95% (2025-09…2026-07) |
| F6 | NAS delay minutes per arrival — CLT — 2025-09…2026-08 | 1.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 71% (2025-09…2026-07) |
| F96 | NAS delay minutes per arrival — ATL — 2025-09…2026-08 | 2.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 80% (2025-09…2026-07) |
| F97 | NAS delay minutes per arrival — AUS — 2025-09…2026-08 | 2.6 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 94% (2025-09…2026-07) |
| F98 | NAS delay minutes per arrival — BNA — 2025-09…2026-08 | 2.9 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 93% (2025-09…2026-07) |
| F99 | NAS delay minutes per arrival — BOS — 2025-09…2026-08 | 7.2 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 75% (2025-09…2026-07) |
| F100 | NAS delay minutes per arrival — BWI — 2025-09…2026-08 | 2.3 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 95% (2025-09…2026-07) |
| F101 | NAS delay minutes per arrival — CLT — 2025-09…2026-08 | 1.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 71% (2025-09…2026-07) |

**Methodology**
- `quantile:nas_delay_min_per_arrival`: 10th percentile (linear interpolation) across 30 airports
- `nas_delay_min_per_arrival`: Σ NAS (airspace/system) delay minutes / operated arrivals
- `rank_score`: Σ weight × minmax_in_set-scaled criterion; criteria: nas_delay_min_per_arrival (higher_better, w=1.0)
- `peak_hour_ops_p95`: 95th percentile over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights
- `pearson_r`: Pearson correlation of [nas_delay_min_per_arrival] and [peak_hour_ops_p95] across airports
- `spearman_rho`: Spearman rank correlation of [nas_delay_min_per_arrival] and [peak_hour_ops_p95] across airports
- `spearman_ci_low`: Spearman ρ 95% bootstrap CI, lower of [nas_delay_min_per_arrival] and [peak_hour_ops_p95] across airports
- `spearman_ci_high`: Spearman ρ 95% bootstrap CI, upper of [nas_delay_min_per_arrival] and [peak_hour_ops_p95] across airports
- `n`: airports used of [nas_delay_min_per_arrival] and [peak_hour_ops_p95] across airports
- `ontime_coverage`: operated reporting-carrier departures (On-Time) / passenger departures (T-100), same window

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- Scores are relative to the airports in this set; adding/removing airports changes them.
- On-Time covers less than 70% of this airport's airline departures; delay/peak figures describe a partial slice.
- Scheduled peak from On-Time is a lower bound on total scheduled operations (reporting carriers only).
- Association across airports, not causation; confounders (size, hub status, region) are not controlled.
- n = 30 airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ.
- On-Time covers domestic flights of reporting carriers only, with no international flights and no small carriers. NAS delay is calculated airspace and system delay minutes per operated arrival. The cause of those minutes is not identified.
- Scheduled peak-hour operations are a lower bound on total scheduled operations because they count reporting carriers only.
- On-Time coverage is measured on 2025-09…2026-07, which is not the same window label as the delay and peak-hour figures 2025-09…2026-08, because coverage uses months shared with T-100.
- EWR is in the high-delay group and carries the partial-slice coverage caveat, as do IAD, IAH, JFK, and MIA. Those airports remain inside the distribution and the full-set correlation.
- A correlation using only the high-delay airports cannot be estimated: the operator returned insufficient_data because that slice is smaller than the minimum sample a correlation requires.
- The correlation does not control for size, hub role, or region. It is not evidence of unmet demand, terminal capacity, fares, or profitability, none of which these metrics measure.
- Rank scores are relative to this large_hub set. They are not a valuation and they are not the investment screening model, so screening flags are not part of the result.