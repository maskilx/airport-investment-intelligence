## NPIAS 2025-2029 development need across report small hubs has median $72.8M

Airports labelled small hubs in the 2025-2029 NPIAS report (hub code S) each have a development-need figure. Those figures are estimated (NPIAS 2025-2029 development estimate). The combined estimate for the set is $6.71B (estimate).

The cross-airport distribution is calculated, with linear interpolation. 10th percentile (linear interpolation) across 74 airports.

- P10: $25.0M
- P25: $41.5M
- P50 (median): $72.8M
- P75: $100.8M
- P90: $151.7M

The interquartile range (P75 minus P25) is $59.3M. The gap from the median up to P90 is $78.9M. The gap from P10 up to the median is $47.8M. The upper gap exceeds the lower gap by $31.2M.

Source: faa_npias [2025-2029]. The metric window label is current release because NPIAS need is a static release; the loaded cycle is 2025-2029.

**Findings and reasoning**
- *Fact*: The combined development-need estimate for airports the 2025-2029 NPIAS report labels as small hubs is $6.71B (estimate), class estimated. [F168]
- *Fact*: Calculated percentiles of airport-level need are P10 $25.0M, P25 $41.5M, P50 $72.8M, P75 $100.8M, and P90 $151.7M. [F163, F164, F165, F166, F167]
- *Fact*: The interquartile range is $59.3M. The median-to-P90 gap is $78.9M and the P10-to-median gap is $47.8M, so the upper gap is larger by $31.2M. [F169, F170, F171, F172]
- *Inference*: Estimated need is uneven and right-skewed: the upper tail extends farther above the median than the lower tail falls below it. [F165, F167, F170, F171, F172]
- *Fact*: An exploratory cross-tab versus the latest FAA hub class counts 72 (exploratory query) airports small on both labels, 2 (exploratory query) small in the report but medium on the latest FAA class, 1 (exploratory query) medium in the report but small on the latest FAA class, and 6 (exploratory query) nonhub in the report but small on the latest FAA class. [F85, F86, F87, F88]

**Assumptions**
- Small hub means hub code S on the NPIAS 2025-2029 airport record. The distribution includes those report-small airports even when the latest FAA enplanement hub class differs, and it excludes airports that are small only on that latest FAA class.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F165 | P50 of npias_need_usd across set | $72.8M | calculated | current release | faa_npias [2025-2029] |  |
| F168 | NPIAS 5-year development need — group total — current release | $6.71B (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F163 | P10 of npias_need_usd across set | $25.0M | calculated | current release | faa_npias [2025-2029] |  |
| F164 | P25 of npias_need_usd across set | $41.5M | calculated | current release | faa_npias [2025-2029] |  |
| F166 | P75 of npias_need_usd across set | $100.8M | calculated | current release | faa_npias [2025-2029] |  |
| F167 | P90 of npias_need_usd across set | $151.7M | calculated | current release | faa_npias [2025-2029] |  |
| F169 | difference(F166, F164) | $59.3M | calculated | current release | current release | faa_npias [2025-2029]; faa_npias [2025-2029] |  |
| F170 | difference(F167, F165) | $78.9M | calculated | current release | current release | faa_npias [2025-2029]; faa_npias [2025-2029] |  |
| F171 | difference(F165, F163) | $47.8M | calculated | current release | current release | faa_npias [2025-2029]; faa_npias [2025-2029] |  |
| F172 | difference(F170, F171) | $31.2M | calculated | current release | current release | current release | current release | faa_npias [2025-2029]; faa_npias [2025-2029]; faa_npias [2025-2029]; faa_npias [2025-2029] |  |
| F88 | n_airports (exploratory query) | 72 (exploratory query) | exploratory | as queried | faa_npias [n/a] |  |
| F87 | n_airports (exploratory query) | 2 (exploratory query) | exploratory | as queried | faa_npias [n/a] |  |
| F85 | n_airports (exploratory query) | 1 (exploratory query) | exploratory | as queried | faa_npias [n/a] |  |
| F86 | n_airports (exploratory query) | 6 (exploratory query) | exploratory | as queried | faa_npias [n/a] |  |
| F89 | NPIAS 5-year development need — ALB — current release | $6.9M (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F90 | NPIAS 5-year development need — ATW — current release | $84,656 (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F91 | NPIAS 5-year development need — AVL — current release | $98.5M (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F92 | NPIAS 5-year development need — AZA — current release | $57.2M (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F93 | NPIAS 5-year development need — BHM — current release | $138.5M (estimate) | estimated | current release | faa_npias [2025-2029] |  |
| F94 | NPIAS 5-year development need — BTV — current release | $88.2M (estimate) | estimated | current release | faa_npias [2025-2029] |  |

**Methodology**
- `quantile:npias_need_usd`: 50th percentile (linear interpolation) across 74 airports
- `npias_need_usd`: NPIAS 2025-2029 development estimate
- `derived:difference`: difference of [P75 of npias_need_usd across set] , [P25 of npias_need_usd across set]
- `exploratory_sql`: column n_airports of: SELECT n.npias_cycle, n.hub AS npias_hub, f.faa_hub_class, count(*) AS n_airports FROM npias_airport n LEFT JOIN dim_airport_faa f ON f.faa_lid = n.locid WHERE n.hub = 'S' OR f.faa_hub_class = 'S' GROUP BY 1, 2, 3 ORDER BY 1, 2, 3

**Caveats and limitations**
- NPIAS figures are sponsor-reported 5-year AIP-eligible NEED estimates, not funding.
- Exploratory SQL: definitions are not catalog metrics; verify before relying on it.
- These are sponsor-reported AIP-eligible development-need estimates for the 2025-2029 cycle, not awarded, approved, or committed funding.
- Unmet demand, terminal capacity, fares, and profitability are not measured here.
- Percentiles are calculated from those estimates. They are not a forecast, a valuation, or a screening rank.
- The percentile summary does not include the lowest or highest airport.
- The hub-label cross-tab is an exploratory query, not a catalog metric.
- Proposed new airports listed separately in the NPIAS report are outside this distribution.