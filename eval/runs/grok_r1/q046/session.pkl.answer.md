## Manchester-Boston Regional (MHT) recent seat factor is 74.9% for the latest covered window and 79.1% in the latest month.

Manchester binds to Manchester-Boston Regional Airport (MHT) in New Hampshire, the only exact city match. For the latest covered window of departing passenger and combi segments, calculated seat factor (passengers divided by seats) is 74.9%. The latest available month is 79.1%. Within that window the highest month is 84.2% and the lowest is 66.3%. A linear fit of the monthly series has slope -0.01 ratio per month. That slope is descriptive and includes seasonality, so it does not establish a structural decline. Seat factor is a calculated ratio. It is not a measure of unmet demand, terminal capacity, fares, or profitability.

**Findings and reasoning**
- *Fact*: Seat factor at MHT for the latest covered window is 74.9%, calculated as passengers divided by seats on departing passenger and combi segments. [F1]
- *Fact*: Seat factor in the latest available month is 79.1%. [F2]
- *Fact*: Inside that same window, the highest monthly seat factor is 84.2% and the lowest is 66.3%. [F5, F12]
- *Inference*: The monthly series has a descriptive slope of -0.01 ratio per month. Because the fit includes seasonality, a structural decline is not established. [F15, F3, F14]

**Assumptions**
- Manchester means Manchester-Boston Regional Airport (MHT) in Manchester, New Hampshire, the sole exact city match from entity resolution. United Kingdom Manchester is outside this US airport catalog.
- Recently means the latest covered window for this metric, the period on 74.9%, reported together with the latest month, 79.1%.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Seat factor — MHT — 2025-08…2026-07 | 74.9% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F2 | Seat factor — MHT — 2026-07 | 79.1% | calculated | 2026-07 | bts_t100_segment [2026-07] |  |
| F5 | Seat factor — month=2025-10 — 2025-08…2026-07 | 84.2% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F12 | Seat factor — month=2026-05 — 2025-08…2026-07 | 66.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F15 | Linear trend per month — seat_factor — MHT | -0.01 ratio per month | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F3 | Seat factor — month=2025-08 — 2025-08…2026-07 | 80.9% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F14 | Seat factor — month=2026-07 — 2025-08…2026-07 | 79.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F4 | Seat factor — month=2025-09 — 2025-08…2026-07 | 78.0% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F6 | Seat factor — month=2025-11 — 2025-08…2026-07 | 72.5% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F7 | Seat factor — month=2025-12 — 2025-08…2026-07 | 72.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F8 | Seat factor — month=2026-01 — 2025-08…2026-07 | 66.7% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |

**Methodology**
- `seat_factor`: Σ passengers / Σ seats, departing passenger/combi segments
- `trend_slope:seat_factor`: OLS slope of monthly seat_factor, 2025-08…2026-07

**Caveats and limitations**
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- Monthly series include seasonality; slope is descriptive.
- Seat factor is calculated from passengers and seats. It is not a directly observed survey result.
- Unmet demand, terminal capacity, fares, and profitability are not measured here, and seat factor is not evidence of them.
- The monthly slope is descriptive and includes seasonality.
- No month later than the latest covered traffic month is available, so a more current reading cannot be established.
- No peer benchmark was computed, so this level is not ranked against other airports.