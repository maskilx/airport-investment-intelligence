## CY 2025 medium-hub gauge centers on 138 seats per departure

Across US airports stored as FAA hub class M, the CY 2025 distribution of average seats per departure (equal weight per airport) is P10 120 seats, P25 125 seats, P50 138 seats, P75 147 seats, and P90 160 seats. The interquartile range, P75 minus P25, is 21.53 seats. The span from P10 to P90 is 39.76 seats.

Each airport figure is calculated: total seats divided by passenger departures on T-100 departing passenger and combi segments over 2025-01…2025-12. Percentiles use linear interpolation. 10th percentile (linear interpolation) across 35 airports.

**Findings and reasoning**
- *Fact*: For FAA hub class M in CY 2025, average seats per departure has P10 120 seats, P25 125 seats, median 138 seats, P75 147 seats, and P90 160 seats. [F36, F37, F38, F39, F40]
- *Fact*: The interquartile range of those airport-level averages is 21.53 seats, and the P10-to-P90 span is 39.76 seats. [F41, F42]
- *Inference*: The middle half of medium hubs lies between 125 seats and 147 seats. That spread describes gauge mix across airports; it does not establish fleet strategy, unmet demand, or profitability. [F37, F39, F41]

**Assumptions**
- Medium hub means the warehouse FAA hub class M on the airport record (latest ACAIS classification stored for that airport), not a hub class recomputed in this analysis from CY 2025 enplanements.
- The distribution weights each airport equally. It is not weighted by departures, seats, or passengers.
- The US set is the resolver group for hub class M, which includes state airports and SJU.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F38 | P50 of seats_per_departure across set | 138 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F36 | P10 of seats_per_departure across set | 120 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F37 | P25 of seats_per_departure across set | 125 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F39 | P75 of seats_per_departure across set | 147 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F40 | P90 of seats_per_departure across set | 160 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F41 | difference(F39, F37) | 21.53 seats | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F42 | difference(F40, F36) | 39.76 seats | calculated | 2025-01…2025-12 | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)]; bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F1 | Average seats per departure (gauge) — ABQ — 2025-01…2025-12 | 126 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F2 | Average seats per departure (gauge) — ANC — 2025-01…2025-12 | 94.55 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F3 | Average seats per departure (gauge) — BDL — 2025-01…2025-12 | 145 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F4 | Average seats per departure (gauge) — BOI — 2025-01…2025-12 | 111 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F5 | Average seats per departure (gauge) — BUF — 2025-01…2025-12 | 123 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F6 | Average seats per departure (gauge) — BUR — 2025-01…2025-12 | 120 seats | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |

**Methodology**
- `quantile:seats_per_departure`: 50th percentile (linear interpolation) across 35 airports
- `derived:difference`: difference of [P75 of seats_per_departure across set] , [P25 of seats_per_departure across set]
- `seats_per_departure`: Σ seats / Σ passenger departures

**Caveats and limitations**
- This is the distribution of airport-level average gauge, not the distribution of seats on individual departures.
- The distribution operator returns P10, P25, P50, P75, and P90 only. Minimum, maximum, and histogram bins are not established here.
- Cargo-only departures are outside the metric, which divides seats by passenger departures.
- Terminal capacity, fares, unmet demand, and profitability are not measured by these data.
- Hub class can differ from an informal medium-hub list if the stored ACAIS classification year is not CY 2025.