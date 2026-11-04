## Monthly anomalies in DEN departure cancellation rates cannot be established for September 2025–August 2026

The time-series anomaly screen (robust z of year-over-year monthly changes) returned no flagged months for departure cancellation rates at Denver International Airport (DEN) from September 2025 through August 2026. That screen can flag a month only when a same-month value from the prior year exists. A request for the prior-year window returned out_of_coverage for on-time departures; the available coverage is September 2025 through August 2026 only. No year-over-year change was scored, so the empty screen is not evidence that every month was typical.

Observed cancellation rates (calculated: cancelled divided by scheduled departures) for each month in the window:

- September 2025: 0.1%
- October 2025: 0.1%
- November 2025: 1.4%
- December 2025: 0.6%
- January 2026: 1.7%
- February 2026: 0.9%
- March 2026: 1.5%
- April 2026: 0.3%
- May 2026: 0.3%
- June 2026: 0.4%
- July 2026: 0.8%
- August 2026: 1.3%

These are calculated rates, not forecasts or estimates. The series does not identify causes.

**Findings and reasoning**
- *Fact*: DEN departure cancellation rates by month were 0.1% in September 2025, 0.1% in October 2025, 1.4% in November 2025, 0.6% in December 2025, 1.7% in January 2026, 0.9% in February 2026, 1.5% in March 2026, 0.3% in April 2026, 0.3% in May 2026, 0.4% in June 2026, 0.8% in July 2026, and 1.3% in August 2026. [F13, F14, F15, F16, F17, F18, F19, F20, F21, F22, F23, F24]

**Assumptions**
- DEN refers to Denver International Airport in Denver, CO, the airport returned by entity resolution.
- Departure cancellation rate means the catalog metric cancel_rate, defined as cancelled divided by scheduled departures on on-time departure records.
- A monthly anomaly means a month flagged by the catalog anomaly operator in time mode, which scores year-over-year changes with a robust z at the default threshold.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F13 | Cancellation rate — month=2025-09 — 2025-09…2026-08 | 0.1% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F14 | Cancellation rate — month=2025-10 — 2025-09…2026-08 | 0.1% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F15 | Cancellation rate — month=2025-11 — 2025-09…2026-08 | 1.4% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F16 | Cancellation rate — month=2025-12 — 2025-09…2026-08 | 0.6% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F17 | Cancellation rate — month=2026-01 — 2025-09…2026-08 | 1.7% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F18 | Cancellation rate — month=2026-02 — 2025-09…2026-08 | 0.9% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F19 | Cancellation rate — month=2026-03 — 2025-09…2026-08 | 1.5% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F20 | Cancellation rate — month=2026-04 — 2025-09…2026-08 | 0.3% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F21 | Cancellation rate — month=2026-05 — 2025-09…2026-08 | 0.3% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F22 | Cancellation rate — month=2026-06 — 2025-09…2026-08 | 0.4% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F23 | Cancellation rate — month=2026-07 — 2025-09…2026-08 | 0.8% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |
| F24 | Cancellation rate — month=2026-08 — 2025-09…2026-08 | 1.3% | calculated | 2025-09…2026-08 | bts_ontime [2025-09…2026-08 (12 periods)] |  |

**Methodology**
- `cancel_rate`: cancelled / scheduled departures

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- On-time departure coverage is September 2025 through August 2026. The prior year is out of coverage, so year-over-year anomalies cannot be established.
- An empty flag list is not a positive finding that each month fell inside a normal range.
- On-time records cover domestic flights of reporting carriers only, and exclude international flights and non-reporting carriers.
- Causes of month-to-month differences are not identified. Terminal capacity, unmet demand, fares, and profitability are not measured here.