## HNL monthly distance-weighted load factor, January 2024 through June 2026, linear slope 0.00 ratio per month

At Daniel K. Inouye International Airport (HNL) in Honolulu, Hawaii, monthly distance-weighted load factor is calculated, not observed: Σ(passengers·distance) / Σ(seats·distance), departing segments (not system RPM/ASM). The series below is every month from January 2024 through June 2026 and pools departing segments for all carriers.

January 2024: 81.9%
February 2024: 80.7%
March 2024: 83.3%
April 2024: 80.8%
May 2024: 83.9%
June 2024: 88.4%
July 2024: 86.3%
August 2024: 89.1%
September 2024: 83.3%
October 2024: 86.6%
November 2024: 80.7%
December 2024: 82.7%
January 2025: 84.7%
February 2025: 83.4%
March 2025: 85.0%
April 2025: 83.3%
May 2025: 86.4%
June 2025: 88.8%
July 2025: 86.1%
August 2025: 88.8%
September 2025: 83.0%
October 2025: 85.8%
November 2025: 80.7%
December 2025: 81.3%
January 2026: 82.5%
February 2026: 81.1%
March 2026: 84.9%
April 2026: 81.5%
May 2026: 86.3%
June 2026: 88.2%

The linear trend per month over that window is 0.00 ratio per month (calculated). Its definition is OLS slope of monthly segment_load_factor, 2024-01…2026-06. Monthly series include seasonality; the slope is descriptive. It is not a seasonally adjusted trend and it is not a forecast. The year-over-year change of the last month is -0.7% (calculated), defined as 2026-06 vs 2025-06. June 2025 was 88.8% and June 2026 was 88.2%.

January 2024, the first month, was 81.9%. June 2026, the last month, was 88.2%. Those months fall in different seasons, so the gap between the endpoints is not a year-over-year rate.

**Findings and reasoning**
- *Fact*: Calculated monthly distance-weighted load factor at HNL was 81.9% in January 2024, 80.7% in February 2024, 83.3% in March 2024, 80.8% in April 2024, 83.9% in May 2024, 88.4% in June 2024, 86.3% in July 2024, 89.1% in August 2024, 83.3% in September 2024, 86.6% in October 2024, 80.7% in November 2024, 82.7% in December 2024, 84.7% in January 2025, 83.4% in February 2025, 85.0% in March 2025, 83.3% in April 2025, 86.4% in May 2025, 88.8% in June 2025, 86.1% in July 2025, 88.8% in August 2025, 83.0% in September 2025, 85.8% in October 2025, 80.7% in November 2025, 81.3% in December 2025, 82.5% in January 2026, 81.1% in February 2026, 84.9% in March 2026, 81.5% in April 2026, 86.3% in May 2026, and 88.2% in June 2026. [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20, F21, F22, F23, F24, F25, F26, F27, F28, F29, F30]
- *Fact*: The descriptive linear slope of the monthly series is 0.00 ratio per month (calculated), defined as OLS slope of monthly segment_load_factor, 2024-01…2026-06. The year-over-year change of the last month is -0.7% (calculated), defined as 2026-06 vs 2025-06. [F31, F32]
- *Inference*: June 2024 88.4% and August 2024 89.1% are above February 2024 80.7% and November 2024 80.7%. June 2025 88.8% and August 2025 88.8% are above February 2025 83.4% and November 2025 80.7%. May 2026 86.3% and June 2026 88.2% are above February 2026 81.1% and April 2026 81.5%. That within-year shape sits inside the linear slope 0.00 ratio per month. The same-month change for June 2026 versus June 2025 is -0.7%. [F2, F6, F8, F11, F14, F18, F20, F23, F26, F28, F29, F30, F31, F32]

**Assumptions**
- Honolulu and the code HNL both resolve to Daniel K. Inouye International Airport in Honolulu, Hawaii. The Urban Honolulu metro candidate is that same airport, so this answer uses the airport.
- The window is January 2024 through June 2026, inclusive, as asked. No fiscal-year window is used.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F31 | Linear trend per month — segment_load_factor — HNL | 0.00 ratio per month | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F1 | Distance-weighted load factor — month=2024-01 — 2024-01…2026-06 | 81.9% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F2 | Distance-weighted load factor — month=2024-02 — 2024-01…2026-06 | 80.7% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F3 | Distance-weighted load factor — month=2024-03 — 2024-01…2026-06 | 83.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F4 | Distance-weighted load factor — month=2024-04 — 2024-01…2026-06 | 80.8% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F5 | Distance-weighted load factor — month=2024-05 — 2024-01…2026-06 | 83.9% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F6 | Distance-weighted load factor — month=2024-06 — 2024-01…2026-06 | 88.4% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F7 | Distance-weighted load factor — month=2024-07 — 2024-01…2026-06 | 86.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F8 | Distance-weighted load factor — month=2024-08 — 2024-01…2026-06 | 89.1% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F9 | Distance-weighted load factor — month=2024-09 — 2024-01…2026-06 | 83.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F10 | Distance-weighted load factor — month=2024-10 — 2024-01…2026-06 | 86.6% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F11 | Distance-weighted load factor — month=2024-11 — 2024-01…2026-06 | 80.7% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F12 | Distance-weighted load factor — month=2024-12 — 2024-01…2026-06 | 82.7% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F13 | Distance-weighted load factor — month=2025-01 — 2024-01…2026-06 | 84.7% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F14 | Distance-weighted load factor — month=2025-02 — 2024-01…2026-06 | 83.4% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F15 | Distance-weighted load factor — month=2025-03 — 2024-01…2026-06 | 85.0% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F16 | Distance-weighted load factor — month=2025-04 — 2024-01…2026-06 | 83.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F17 | Distance-weighted load factor — month=2025-05 — 2024-01…2026-06 | 86.4% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F18 | Distance-weighted load factor — month=2025-06 — 2024-01…2026-06 | 88.8% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F19 | Distance-weighted load factor — month=2025-07 — 2024-01…2026-06 | 86.1% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F20 | Distance-weighted load factor — month=2025-08 — 2024-01…2026-06 | 88.8% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F21 | Distance-weighted load factor — month=2025-09 — 2024-01…2026-06 | 83.0% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F22 | Distance-weighted load factor — month=2025-10 — 2024-01…2026-06 | 85.8% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F23 | Distance-weighted load factor — month=2025-11 — 2024-01…2026-06 | 80.7% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F24 | Distance-weighted load factor — month=2025-12 — 2024-01…2026-06 | 81.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F25 | Distance-weighted load factor — month=2026-01 — 2024-01…2026-06 | 82.5% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F26 | Distance-weighted load factor — month=2026-02 — 2024-01…2026-06 | 81.1% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F27 | Distance-weighted load factor — month=2026-03 — 2024-01…2026-06 | 84.9% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F28 | Distance-weighted load factor — month=2026-04 — 2024-01…2026-06 | 81.5% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F29 | Distance-weighted load factor — month=2026-05 — 2024-01…2026-06 | 86.3% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F30 | Distance-weighted load factor — month=2026-06 — 2024-01…2026-06 | 88.2% | calculated | 2024-01…2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |
| F32 | YoY change of last month — segment_load_factor — HNL | -0.7% | calculated | 2026-06 | bts_t100_segment [2024-01…2026-06 (30 periods)] |  |

**Methodology**
- `trend_slope:segment_load_factor`: OLS slope of monthly segment_load_factor, 2024-01…2026-06
- `segment_load_factor`: Σ(passengers·distance) / Σ(seats·distance), departing segments (not system RPM/ASM)
- `yoy:segment_load_factor`: 2026-06 vs 2025-06

**Caveats and limitations**
- Monthly series include seasonality; slope is descriptive.
- The metric is the catalog distance-weighted load factor on departing segments. It is not a network-wide load factor.
- Each monthly value is calculated from segment passengers, seats, and distance. It is not a direct cabin observation.
- Unmet demand, terminal capacity, fares, and profitability are not measured and are not established.
- The linear slope includes seasonality. It is descriptive only. It is not seasonally adjusted and it is not a forecast.
- Causes of the within-year shape are not identified.
- All carriers and all destinations, domestic and international, are pooled. No carrier split and no route split is included.
- Departing-segment coverage in the catalog extends past June 2026, including July 2026. This answer stops at the requested end month.
- This is not a screening rank and not a valuation.