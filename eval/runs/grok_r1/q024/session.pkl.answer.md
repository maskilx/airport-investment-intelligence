## No anomalous year-over-year passenger months at MIA, January 2024–June 2026

The time-series anomaly screen on monthly enplaned passengers at Miami International Airport (MIA) flagged no month from January 2024 through June 2026. The screen scores each month’s year-over-year change against the airport’s own year-over-year history using a robust z-score, at the catalog default threshold. Months in 2024 are the comparison baseline and are not scored, because this passenger series begins in January 2024. Observed enplanements run from 2.40M passengers in January 2024 to 2.13M passengers in June 2026. June 2026 was -6.0% versus June 2025 (calculated). A descriptive linear fit over the same monthly series slopes at -2,278 passengers per month (calculated); that slope includes seasonality and is not an anomaly flag.

**Findings and reasoning**
- *Fact*: Monthly enplaned passengers at MIA are observed from January 2024 (2.40M passengers) through June 2026 (2.13M passengers). The trend window covering those months is 2024-01…2026-06. [F32, F61, F62]
- *Fact*: June 2026 enplanements (2.13M passengers, observed) were -6.0% versus June 2025 (2.26M passengers, observed). This year-over-year change is calculated for the last month of the window and is not an anomaly flag. [F63, F61, F49]
- *Inference*: On this same monthly series, the time-series anomaly screen returned no flagged months, so no scored month had a year-over-year change that was unusual relative to the airport’s own year-over-year history under the default robust-z rule. [F62, F32, F61, F63]

**Assumptions**
- MIA is Miami International Airport in Miami, FL, the unique airport resolved from that name and code.
- An anomaly here means the catalog time-series screen: a robust z-score of the monthly year-over-year change in enplaned passengers versus the airport’s own history, at the default threshold. It is not a cross-airport outlier test and not a judgment about demand, capacity, or operations.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F32 | Enplaned passengers — month=2024-01 — 2024-01…2026-06 | 2.40M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F61 | Enplaned passengers — month=2026-06 — 2024-01…2026-06 | 2.13M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F63 | YoY change of last month — passengers — MIA | -6.0% | calculated | 2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F62 | Linear trend per month — passengers — MIA | -2,278 passengers per month | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F49 | Enplaned passengers — month=2025-06 — 2024-01…2026-06 | 2.26M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F33 | Enplaned passengers — month=2024-02 — 2024-01…2026-06 | 2.24M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F34 | Enplaned passengers — month=2024-03 — 2024-01…2026-06 | 2.50M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F35 | Enplaned passengers — month=2024-04 — 2024-01…2026-06 | 2.27M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F36 | Enplaned passengers — month=2024-05 — 2024-01…2026-06 | 2.34M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F37 | Enplaned passengers — month=2024-06 — 2024-01…2026-06 | 2.21M passengers | observed | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |

**Methodology**
- `passengers`: Σ passengers on departing passenger/combi segments
- `yoy:passengers`: 2026-06 vs 2025-06
- `trend_slope:passengers`: OLS slope of monthly passengers, 2024-01…2026-06

**Caveats and limitations**
- T-100 passengers are segment enplanements (connecting passengers count at each enplanement).
- Monthly series include seasonality; slope is descriptive.
- The screen flags unusual year-over-year changes and does not identify causes.
- Calendar 2024 cannot be tested for a year-over-year anomaly because there is no earlier year in this passenger series.
- A seasonal level that repeats is not flagged when the prior year was similar. The test is on the change, not the level.
- Unmet demand, terminal capacity, fares, and profitability are not measured by these data.
- The screen emits a finding only for a flagged month, so the empty result is the operator output rather than a stored count of anomalies.
- Passenger coverage in this catalog extends through July 2026; July 2026 was outside the requested window and was not screened.