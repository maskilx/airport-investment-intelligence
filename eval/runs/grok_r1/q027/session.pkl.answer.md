## ORD weather-delay minutes per arrival exceed ATL by 1.1 min over the reporting-carrier window

Over 2025-09…2026-08, calculated weather delay minutes per operated arrival were 1.8 min at ORD and 0.7 min at ATL. ORD exceeds ATL by 1.1 min, which is 157.4% higher than the ATL rate. These values are calculated: weather-cause minutes divided by operated arrivals for domestic reporting carriers. They are not observed raw totals and they are not forecasts.

**Findings and reasoning**
- *Fact*: Over 2025-09…2026-08, weather delay minutes per arrival at ORD were 1.8 min. [F2]
- *Fact*: Over 2025-09…2026-08, weather delay minutes per arrival at ATL were 0.7 min. [F1]
- *Fact*: ORD minus ATL on this metric is 1.1 min, which is 157.4% higher than the ATL rate. [F3, F4]
- *Inference*: Within the domestic reporting-carrier sample, ORD shows a higher weather-coded delay per arrival than ATL over the same window. [F2, F1, F3]

**Assumptions**
- The reporting-carrier window is the full On-Time arrivals coverage span, 2025-09…2026-08.
- ORD is Chicago O’Hare International Airport. ATL is Hartsfield Jackson Atlanta International Airport. The spelled Atlanta name did not resolve; the code ATL matched that airport alone.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F3 | difference(F2, F1) | 1.1 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F2 | Weather delay minutes per arrival — ORD — 2025-09…2026-08 | 1.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 82% (2025-09…2026-07) |
| F1 | Weather delay minutes per arrival — ATL — 2025-09…2026-08 | 0.7 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 80% (2025-09…2026-07) |
| F4 | pct_difference(F2, F1) | 157.4% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |

**Methodology**
- `derived:difference`: difference of [Weather delay minutes per arrival — ORD — 2025-09…2026-08] , [Weather delay minutes per arrival — ATL — 2025-09…2026-08]
- `weather_delay_min_per_arrival`: Σ weather delay minutes / operated arrivals
- `derived:pct_difference`: pct_difference of [Weather delay minutes per arrival — ORD — 2025-09…2026-08] , [Weather delay minutes per arrival — ATL — 2025-09…2026-08]

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- On-Time data cover domestic flights of reporting carriers only. International flying and non-reporting carriers are outside these rates.
- The metric uses only the weather cause code. Minutes coded to NAS, the carrier, or late aircraft, and cancellations, are not included, so this is not all weather-related disruption.
- The comparison does not establish a cause. Weather severity, airline coding practice, and schedule mix are not identified.
- Unmet demand, terminal capacity, fares, and profitability are not measured by these data.
- Coverage versus T-100 passenger departures, shown with the evidence, uses overlapping months only and therefore stops short of the final month in 2025-09…2026-08.
- Each rate is the window sum of weather-delay minutes divided by operated arrivals. This comparison does not establish the gap in each month.