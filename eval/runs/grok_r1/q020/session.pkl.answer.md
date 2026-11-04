## Large-hub median taxi-out centers on 17.0 min over the On-Time window

For 2025-09…2026-08, the equal-weighted distribution of median taxi-out across FAA hub class L is P10 14.9 min, P25 16.0 min, P50 17.0 min, P75 19.0 min, and P90 21.1 min. Source: bts_ontime [2025-09…2026-08 (12 periods)].

Each airport value is the calculated median of taxi-out on operated departures in the On-Time reporting data. The cross-airport percentiles are calculated and use linear interpolation. 10th percentile (linear interpolation) across 30 airports.

The interquartile range, P75 minus P25, is 3.0 min. The span from P10 to P90 is 6.2 min. The distribution count matches hub class L membership: every airport in that group has a median, and no enplanement threshold excluded anyone. Airports are weighted equally.

**Findings and reasoning**
- *Fact*: Over 2025-09…2026-08, the equal-weighted distribution of airport median taxi-out for FAA hub class L is P10 14.9 min, P25 16.0 min, P50 17.0 min, P75 19.0 min, and P90 21.1 min. These percentiles are calculated. [F31, F32, F33, F34, F35]
- *Fact*: The interquartile range is 3.0 min and the P10-to-P90 span is 6.2 min. Both are calculated. [F36, F37]
- *Inference*: The central band from P25 to P75 runs from 16.0 min to 19.0 min, a spread of 3.0 min. That band describes how typical taxi-out differs across large hubs. It does not establish causes, unmet demand, terminal capacity, fares, or profitability. [F32, F34, F36]

**Assumptions**
- The term large hub did not resolve to an airport, city, or region. large_hub is bound to the catalog group filter hub class L, the FAA large-hub code on the stored airport record, not a class recomputed for this window.
- The window is the full On-Time coverage span, 2025-09…2026-08.
- Each airport counts once. The distribution is not weighted by departures, seats, or passengers.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F33 | P50 of median_taxi_out_min across set | 17.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F31 | P10 of median_taxi_out_min across set | 14.9 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F32 | P25 of median_taxi_out_min across set | 16.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F34 | P75 of median_taxi_out_min across set | 19.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F35 | P90 of median_taxi_out_min across set | 21.1 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F36 | difference(F34, F32) | 3.0 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F37 | difference(F35, F31) | 6.2 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F1 | Median taxi-out — ATL — 2025-09…2026-08 | 15.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 80% (2025-09…2026-07) |
| F2 | Median taxi-out — AUS — 2025-09…2026-08 | 14.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 94% (2025-09…2026-07) |
| F3 | Median taxi-out — BNA — 2025-09…2026-08 | 15.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 93% (2025-09…2026-07) |
| F4 | Median taxi-out — BOS — 2025-09…2026-08 | 19.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 75% (2025-09…2026-07) |
| F5 | Median taxi-out — BWI — 2025-09…2026-08 | 13.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 95% (2025-09…2026-07) |
| F6 | Median taxi-out — CLT — 2025-09…2026-08 | 18.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 71% (2025-09…2026-07) |

**Methodology**
- `quantile:median_taxi_out_min`: 50th percentile (linear interpolation) across 30 airports
- `derived:difference`: difference of [P75 of median_taxi_out_min across set] , [P25 of median_taxi_out_min across set]
- `median_taxi_out_min`: median taxi-out, operated departures

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- This is the distribution of airport-level medians, not the distribution of taxi-out minutes on individual flights.
- The distribution operator returns P10, P25, P50, P75, and P90 only. Minimum, maximum, and histogram bins are not established.
- On-Time coverage versus T-100 passenger departures is attached to each airport median and is not summarized by these percentiles. That coverage ratio uses only months shared with T-100, so it does not cover the full median window.
- Ties among airport medians are not flagged by this operator.
- Unmet demand, terminal capacity, fares, and profitability are not measured. Causes of longer taxi-out are not identified.