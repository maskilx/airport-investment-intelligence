## O’Hare is more congested than Midway on taxi-out and NAS delay

Of the Chicago airports in this comparison, Chicago O’Hare (ORD) is more congested than Chicago Midway (MDW) on taxi-out and NAS (airspace/system) delay. Average taxi-out was 28.2 min at ORD and 15.4 min at MDW, a calculated gap of 12.8 min. Median taxi-out was 25.0 min at ORD and 13.0 min at MDW. NAS delay per arrival was 7.3 min at ORD and 2.3 min at MDW, a calculated gap of 4.9 min. Average departure delay was 22.3 min at ORD and 16.6 min at MDW. The arrival delay rate was 26.3% at ORD and 22.9% at MDW, and the cancellation rate was 2.9% at ORD and 1.6% at MDW. The departure delay rate is the exception: 28.4% at MDW versus 26.5% at ORD, and the calculated MDW minus ORD gap is 1.9%. Weather delay per arrival was 1.7 min at ORD and 0.4 min at MDW. The catalog scheduled peak-hour metric was 154 operations/hour at ORD and 34 operations/hour at MDW. Those peak figures are observed schedule counts, not a congestion rate.

**Findings and reasoning**
- *Fact*: Average taxi-out over the comparison window was 28.2 min at ORD and 15.4 min at MDW. [F22, F21]
- *Fact*: The calculated ORD minus MDW average taxi-out gap is 12.8 min. [F39]
- *Fact*: Median taxi-out was 25.0 min at ORD and 13.0 min at MDW. [F24, F23]
- *Fact*: NAS delay per arrival was 7.3 min at ORD and 2.3 min at MDW. [F32, F31]
- *Fact*: The calculated ORD minus MDW NAS-delay gap is 4.9 min. [F41]
- *Fact*: Average departure delay was 22.3 min at ORD and 16.6 min at MDW. [F30, F29]
- *Fact*: The arrival delay rate was 26.3% at ORD and 22.9% at MDW. [F28, F27]
- *Fact*: The cancellation rate was 2.9% at ORD and 1.6% at MDW. [F36, F35]
- *Fact*: The departure delay rate was 28.4% at MDW and 26.5% at ORD. The calculated MDW minus ORD gap is 1.9%. [F25, F26, F40]
- *Fact*: Weather delay per arrival was 1.7 min at ORD and 0.4 min at MDW. [F34, F33]
- *Fact*: The catalog scheduled peak-hour metric was 154 operations/hour at ORD and 34 operations/hour at MDW. [F38, F37]
- *Inference*: ORD is the more congested Chicago airport when congestion is read from taxi-out and NAS delay. Those gaps line up with a higher average departure delay, a higher arrival delay rate, and a higher cancellation rate at ORD. The higher departure delay rate at MDW means a larger share of MDW departures were late, which is a different statistic from how long aircraft waited or how much airspace delay they absorbed. [F22, F21, F39, F24, F23, F32, F31, F41, F30, F29, F28, F27, F36, F35, F25, F26, F40]

**Assumptions**
- Chicago is bound to the airports in the Chicago-Naperville-Elgin, IL-IN CBSA that are in the city of Chicago: Chicago O’Hare International (ORD) and Chicago Midway International (MDW). Chicago Rockford International is in Rockford, in a different CBSA, and is excluded.
- More congested is judged primarily by average and median taxi-out and by NAS delay per arrival. Average departure delay, arrival delay rate, and cancellation rate are supporting operational-stress measures. The departure delay rate is reported separately because it ranks these airports in the opposite direction.
- The comparison uses the latest window those On-Time metrics fully cover, which is the window labeled on the findings.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F22 | Average taxi-out — ORD — 2025-09…2026-07 | 28.2 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F21 | Average taxi-out — MDW — 2025-09…2026-07 | 15.4 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F39 | difference(F22, F21) | 12.8 min | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F24 | Median taxi-out — ORD — 2025-09…2026-07 | 25.0 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F23 | Median taxi-out — MDW — 2025-09…2026-07 | 13.0 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F32 | NAS delay minutes per arrival — ORD — 2025-09…2026-07 | 7.3 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F31 | NAS delay minutes per arrival — MDW — 2025-09…2026-07 | 2.3 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F41 | difference(F32, F31) | 4.9 min | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F30 | Average departure delay — ORD — 2025-09…2026-07 | 22.3 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F29 | Average departure delay — MDW — 2025-09…2026-07 | 16.6 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F28 | Arrival delay rate (≥15 min) — ORD — 2025-09…2026-07 | 26.3% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F27 | Arrival delay rate (≥15 min) — MDW — 2025-09…2026-07 | 22.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F36 | Cancellation rate — ORD — 2025-09…2026-07 | 2.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F35 | Cancellation rate — MDW — 2025-09…2026-07 | 1.6% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F25 | Departure delay rate (≥15 min) — MDW — 2025-09…2026-07 | 28.4% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F26 | Departure delay rate (≥15 min) — ORD — 2025-09…2026-07 | 26.5% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F40 | difference(F25, F26) | 1.9% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F34 | Weather delay minutes per arrival — ORD — 2025-09…2026-07 | 1.7 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F33 | Weather delay minutes per arrival — MDW — 2025-09…2026-07 | 0.4 min | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F38 | Scheduled peak hour (95th percentile) — ORD — 2025-09…2026-07 | 154 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F37 | Scheduled peak hour (95th percentile) — MDW — 2025-09…2026-07 | 34 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |

**Methodology**
- `avg_taxi_out_min`: Σ taxi-out minutes / flights with taxi-out
- `derived:difference`: difference of [Average taxi-out — ORD — 2025-09…2026-07] , [Average taxi-out — MDW — 2025-09…2026-07]
- `median_taxi_out_min`: median taxi-out, operated departures
- `nas_delay_min_per_arrival`: Σ NAS (airspace/system) delay minutes / operated arrivals
- `avg_dep_delay_min`: Σ departure delay minutes (early = 0) / operated departures
- `arr_delay15_rate`: arrivals ≥15 min late / operated arrivals
- `cancel_rate`: cancelled / scheduled departures
- `dep_delay15_rate`: departures ≥15 min late / operated departures
- `weather_delay_min_per_arrival`: Σ weather delay minutes / operated arrivals
- `peak_hour_ops_p95`: 95th percentile over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- Scheduled peak from On-Time is a lower bound on total scheduled operations (reporting carriers only).
- On-Time statistics cover domestic flights of reporting carriers only. International flights and small carriers are excluded. On-Time coverage of airline departures was 81.8% at ORD and 94.3% at MDW. International seat share over the same window was 16.5% at ORD and 3.4% at MDW, so a larger share of ORD seats sits outside the domestic On-Time sample.
- Weather delay per arrival was 1.7 min at ORD and 0.4 min at MDW. The dataset does not allocate the taxi-out gap across weather, airline scheduling, and airfield or airspace capacity. NAS delay is the airspace/system component, not a causal attribution.
- Scheduled peak-hour operations are a lower bound because they include reporting carriers only. Open-runway counts are 8 runways at ORD and 4 runways at MDW, but runway count is not capacity. Peak operations are not converted into a utilization rate.
- Terminal capacity, unmet demand, fares, and profitability are not measured here. This comparison is not a valuation and not an investment screen.