## SFO arrival delays sit above the US pool, with higher NAS minutes and lower weather-cause minutes

These values are calculated from domestic On-Time arrivals over 2025-09…2026-08, the default trailing twelve months. They are not forecasts or estimates.

San Francisco International (SFO) had an arrival delay rate of 33.7%. The arrival-weighted pool of US airports in the commercial enplanement group was 22.7%. The absolute gap in the rate (SFO minus that pool) is 11.0%. Relative to the pool, SFO is 48.4% higher.

NAS (airspace and system) delay minutes per arrival were 10.6 min at SFO and 3.5 min in that pool. The absolute gap is 7.1 min. The relative gap is 203.9%.

Weather delay minutes per arrival were 0.8 min at SFO and 1.0 min in the pool. SFO is lower on this category: the absolute gap is -0.2 min and the relative gap is -23.3%.

The same pattern appears against FAA large hubs, so the gap is not only a contrast with smaller airports. The large-hub arrival delay rate is 22.7% (SFO gap 11.1%). Large-hub NAS minutes per arrival are 4.2 min (absolute gap 6.5 min, relative gap 156.5%). Large-hub weather minutes per arrival are 1.0 min (SFO gap -0.2 min).

The data do not establish why SFO is delayed. The higher arrival delay rate coincides with higher NAS minutes per arrival, and it does not coincide with higher weather-cause minutes. That is a comparison of recorded delay-cause categories, not a physical cause.

**Findings and reasoning**
- *Fact*: Over 2025-09…2026-08, the SFO arrival delay rate was 33.7%, versus 22.7% for the arrival-weighted US commercial pool. [F1, F4]
- *Fact*: The absolute gap in that rate (SFO minus the pool) is 11.0%. Relative to the pool, SFO is 48.4% higher. [F10, F11]
- *Fact*: SFO NAS delay minutes per arrival were 10.6 min, versus 3.5 min in the US commercial pool. The absolute gap is 7.1 min and the relative gap is 203.9%. [F2, F5, F12, F13]
- *Fact*: SFO weather delay minutes per arrival were 0.8 min, versus 1.0 min in the US commercial pool. The absolute gap is -0.2 min and the relative gap is -23.3%. SFO is below the pool on weather-cause minutes. [F3, F6, F14, F15]
- *Fact*: Versus FAA large hubs, the arrival delay rate is 22.7% (SFO gap 11.1%), NAS minutes per arrival are 4.2 min (absolute gap 6.5 min, relative gap 156.5%), and weather minutes per arrival are 1.0 min (SFO gap -0.2 min). [F7, F8, F9, F16, F17, F18, F19]
- *Inference*: The elevated arrival delay rate lines up with elevated NAS (airspace and system) minutes per arrival. It does not line up with elevated weather-cause minutes, which are lower at SFO than in both pools. This describes which recorded category is high. It does not identify a meteorological, capacity, or demand cause. [F1, F2, F3, F10, F12, F14, F16, F17, F19]

**Assumptions**
- SFO is San Francisco International Airport, the unique airport match for that code.
- National average means the arrival-weighted group total of each metric (a ratio of sums across airports), not the unweighted mean of airport-level rates.
- The national set is US airports passing the catalog commercial enplanement group filter. An unrestricted US airport set was rejected as too large to aggregate.
- Both pools include SFO, so each gap compares SFO with a benchmark that already contains SFO.
- Large-hub results are a peer check using the FAA large-hub class. They are not the national average.
- The window is the default trailing twelve months of On-Time data, 2025-09…2026-08.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Arrival delay rate (≥15 min) — SFO — 2025-09…2026-08 | 33.7% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F4 | Arrival delay rate (≥15 min) — group total — 2025-09…2026-08 | 22.7% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 77% (2025-09…2026-07) |
| F10 | difference(F1, F4) | 11.0% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F11 | pct_difference(F1, F4) | 48.4% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F2 | NAS delay minutes per arrival — SFO — 2025-09…2026-08 | 10.6 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F5 | NAS delay minutes per arrival — group total — 2025-09…2026-08 | 3.5 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 77% (2025-09…2026-07) |
| F12 | difference(F2, F5) | 7.1 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F13 | pct_difference(F2, F5) | 203.9% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F3 | Weather delay minutes per arrival — SFO — 2025-09…2026-08 | 0.8 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F6 | Weather delay minutes per arrival — group total — 2025-09…2026-08 | 1.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 77% (2025-09…2026-07) |
| F14 | difference(F3, F6) | -0.2 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F15 | pct_difference(F3, F6) | -23.3% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F7 | Arrival delay rate (≥15 min) — group total — 2025-09…2026-08 | 22.7% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F16 | difference(F1, F7) | 11.1% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F8 | NAS delay minutes per arrival — group total — 2025-09…2026-08 | 4.2 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F17 | difference(F2, F8) | 6.5 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F18 | pct_difference(F2, F8) | 156.5% | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F9 | Weather delay minutes per arrival — group total — 2025-09…2026-08 | 1.0 min | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] | 78% (2025-09…2026-07) |
| F19 | difference(F3, F9) | -0.2 min | calculated | 2025-09…2026-08 | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)]; bts_ontime [2025-09…2026-08 (12 periods)] |  |

**Methodology**
- `arr_delay15_rate`: arrivals ≥15 min late / operated arrivals
- `derived:difference`: difference of [Arrival delay rate (≥15 min) — SFO — 2025-09…2026-08] , [Arrival delay rate (≥15 min) — group total — 2025-09…2026-08]
- `derived:pct_difference`: pct_difference of [Arrival delay rate (≥15 min) — SFO — 2025-09…2026-08] , [Arrival delay rate (≥15 min) — group total — 2025-09…2026-08]
- `nas_delay_min_per_arrival`: Σ NAS (airspace/system) delay minutes / operated arrivals
- `weather_delay_min_per_arrival`: Σ weather delay minutes / operated arrivals

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- A cause of the delays is not established. Unmet demand, terminal capacity, fares, and profitability are not measured by these metrics.
- NAS minutes are airspace and system delay minutes per operated arrival. Weather minutes are the weather delay-cause category per operated arrival. Neither is a weather observation, a runway-capacity measure, or a forecast.
- Carrier delay, late-aircraft delay, and security delay are not catalog metrics, so this is not a full delay-cause decomposition.
- On-Time covers domestic flights of reporting carriers only, so international flights and smaller carriers are excluded. That scope matters at SFO. The low-coverage caveat was not attached. Coverage is computed on months shared with T-100, which does not include every month of the On-Time window.
- Results are a descriptive comparison. They are not a screening rank and not a valuation.