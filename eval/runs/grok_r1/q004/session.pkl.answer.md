## LAX schedules a higher peak hour than SNA and has a higher tight-capacity passenger share, on a larger and longer runway plant

Over 2025-09…2026-07, Los Angeles International (LAX) and John Wayne Orange County in Santa Ana (SNA) differ on both requested measures. The scheduled peak-hour rate is 85 operations/hour at LAX and 22 operations/hour at SNA (LAX minus SNA 63 operations/hour, ratio 3.864). The busiest scheduled hour is 103 operations/hour at LAX and 27 operations/hour at SNA (difference 76 operations/hour, ratio 3.815). Tight-capacity passenger share is 48.7% at LAX and 29.7% at SNA (share difference 19.0%, relative difference 64.1%). Open runways are 4 runways at LAX and 2 runways at SNA (difference 2 runways, ratio 2.000). Percentile peak per open runway is 21.250 at LAX and 11.000 at SNA, so that ratio is 1.932 rather than 3.864. Exploratory dimension figures put the longest runway at 12,894 (exploratory query) feet at LAX and 5,700 (exploratory query) feet at SNA, and the long-runway count at 4 (exploratory query) versus 0 (exploratory query). These peaks are domestic reporting-carrier lower bounds: On-Time coverage of airline departures is 74.6% at LAX and 87.8% at SNA.

**Findings and reasoning**
- *Fact*: During 2025-09…2026-07, the scheduled peak-hour percentile rate is 85 operations/hour at LAX and 22 operations/hour at SNA. The difference is 63 operations/hour and the LAX-to-SNA ratio is 3.864. [F40, F41, F42, F43]
- *Fact*: The busiest scheduled hour in the same window is 103 operations/hour at LAX and 27 operations/hour at SNA. The difference is 76 operations/hour and the ratio is 3.815. [F5, F6, F13, F14]
- *Fact*: Using Passengers on capacity-tight route-months (threshold=0.85) — LAX — 2025-09…2026-07, the tight-capacity passenger share is 48.7% at LAX and 29.7% at SNA. The difference in shares is 19.0%. Relative to SNA, the LAX share is higher by 64.1%. [F7, F8, F15, F16]
- *Fact*: The catalog open-runway count is 4 runways at LAX and 2 runways at SNA. The difference is 2 runways and the ratio is 2.000. [F9, F10, F46, F21]
- *Fact*: Exploratory airport-dimension figures, not catalog metrics, show a longest runway of 12,894 (exploratory query) feet at LAX and 5,700 (exploratory query) feet at SNA (difference 7,194 (exploratory query) feet, ratio 2.262 (exploratory query)). The long-runway count (runways_7000ft_plus (exploratory query)) is 4 (exploratory query) at LAX and 0 (exploratory query) at SNA (difference 4 (exploratory query)). [F27, F34, F47, F48, F28, F35, F49]
- *Fact*: Percentile peak divided by open runways is 21.250 at LAX and 11.000 at SNA (difference 10.250, ratio 1.932). Busiest scheduled hour divided by open runways is 25.750 at LAX and 13.500 at SNA (difference 12.250, ratio 1.907). [F44, F45, F54, F53, F19, F20, F55, F52]
- *Fact*: On-Time coverage of airline departures is 74.6% at LAX and 87.8% at SNA (LAX minus SNA -13.2%). International seat share is 30.5% at LAX and 2.2% at SNA (difference 28.4%). [F36, F37, F50, F38, F39, F51]
- *Inference*: Scaling the scheduled peak by the open-runway count narrows the LAX-to-SNA percentile ratio from 3.864 to 1.932, and the busiest-hour ratio from 3.815 to 1.907. Runway count therefore does not account for the whole peak gap. This ratio is a normalization, not a measured runway-utilization or acceptance rate. The runways are also unequal in length: the longest-runway ratio is 2.262 (exploratory query) and the long-runway-count difference is 4 (exploratory query). [F43, F53, F14, F52, F54, F55, F48, F49]
- *Inference*: Because On-Time coverage is lower at LAX by -13.2% and international seat share is higher at LAX by 28.4%, the scheduled-peak comparison leaves out a larger share of LAX flying than of SNA flying. The amount by which international and non-reporting flights would raise the LAX peak is not established. [F36, F37, F50, F38, F39, F51, F40, F41]

**Assumptions**
- Santa Ana is bound to John Wayne Orange County International Airport (SNA). LAX is bound to Los Angeles International Airport, not the Los Angeles-Long Beach-Anaheim group that also contains SNA.
- Flow metrics share the window 2025-09…2026-07. Open-runway counts are the static catalog snapshot. Longest-runway and long-runway counts are exploratory reads of the airport dimension.
- Tight-capacity passenger share uses the catalog default threshold, as named in Passengers on capacity-tight route-months (threshold=0.85) — LAX — 2025-09…2026-07.
- Per-runway figures divide a scheduled-peak statistic by the count of open runways only. They do not adjust for length, dependence between runways, or hours the airport may operate.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F40 | Scheduled peak hour (95th percentile) — LAX — 2025-09…2026-07 | 85 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 75% (2025-09…2026-07) |
| F41 | Scheduled peak hour (95th percentile) — SNA — 2025-09…2026-07 | 22 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 88% (2025-09…2026-07) |
| F42 | difference(F40, F41) | 63 operations/hour | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F43 | ratio(F40, F41) | 3.864 | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F5 | Busiest scheduled hour — LAX — 2025-09…2026-07 | 103 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 75% (2025-09…2026-07) |
| F6 | Busiest scheduled hour — SNA — 2025-09…2026-07 | 27 operations/hour | observed | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 88% (2025-09…2026-07) |
| F13 | difference(F5, F6) | 76 operations/hour | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F14 | ratio(F5, F6) | 3.815 | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F7 | Passengers on capacity-tight route-months (threshold=0.85) — LAX — 2025-09…2026-07 | 48.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F8 | Passengers on capacity-tight route-months (threshold=0.85) — SNA — 2025-09…2026-07 | 29.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F15 | difference(F7, F8) | 19.0% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F16 | pct_difference(F7, F8) | 64.1% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F9 | Open runways — LAX — current release | 4 runways | observed | current release | ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F10 | Open runways — SNA — current release | 2 runways | observed | current release | ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F46 | difference(F9, F10) | 2 runways | calculated | current release | current release | ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F21 | ratio(F9, F10) | 2.000 | calculated | current release | current release | ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F44 | ratio(F40, F9) | 21.250 | calculated | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F45 | ratio(F41, F10) | 11.000 | calculated | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F53 | ratio(F44, F45) | 1.932 | calculated | 2025-09…2026-07 | current release | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F27 | longest_runway_ft (exploratory query) | 12,894 (exploratory query) | exploratory | as queried |  |  |
| F34 | longest_runway_ft (exploratory query) | 5,700 (exploratory query) | exploratory | as queried |  |  |
| F28 | runways_7000ft_plus (exploratory query) | 4 (exploratory query) | exploratory | as queried |  |  |
| F35 | runways_7000ft_plus (exploratory query) | 0 (exploratory query) | exploratory | as queried |  |  |
| F36 | On-Time coverage of airline departures — LAX — 2025-09…2026-07 | 74.6% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 75% (2025-09…2026-07) |
| F37 | On-Time coverage of airline departures — SNA — 2025-09…2026-07 | 87.8% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] | 88% (2025-09…2026-07) |
| F47 | difference(F27, F34) | 7,194 (exploratory query) | exploratory | as queried | as queried |  |  |
| F48 | ratio(F27, F34) | 2.262 (exploratory query) | exploratory | as queried | as queried |  |  |
| F49 | difference(F28, F35) | 4 (exploratory query) | exploratory | as queried | as queried |  |  |
| F54 | difference(F44, F45) | 10.250 | calculated | 2025-09…2026-07 | current release | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F19 | ratio(F5, F9) | 25.750 | calculated | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F20 | ratio(F6, F10) | 13.500 | calculated | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F55 | difference(F19, F20) | 12.250 | calculated | 2025-09…2026-07 | current release | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F52 | ratio(F19, F20) | 1.907 | calculated | 2025-09…2026-07 | current release | 2025-09…2026-07 | current release | bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)]; bts_ontime [2025-09…2026-07 (11 periods)]; ourairports [2026-11-04]; bts_t100_segment [2024-01…2026-07 (31 periods)] |  |
| F50 | difference(F36, F37) | -13.2% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F38 | International seat share — LAX — 2025-09…2026-07 | 30.5% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F39 | International seat share — SNA — 2025-09…2026-07 | 2.2% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F51 | difference(F38, F39) | 28.4% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] |  |

**Methodology**
- `peak_hour_ops_p95`: 95th percentile over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights
- `derived:difference`: difference of [Scheduled peak hour (95th percentile) — LAX — 2025-09…2026-07] , [Scheduled peak hour (95th percentile) — SNA — 2025-09…2026-07]
- `derived:ratio`: ratio of [Scheduled peak hour (95th percentile) — LAX — 2025-09…2026-07] , [Scheduled peak hour (95th percentile) — SNA — 2025-09…2026-07]
- `peak_hour_ops_max`: maximum over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights
- `tight_capacity_pax_share(threshold=0.85)`: share of departing passengers on route-months with passengers/seats ≥ 0.85
- `derived:pct_difference`: pct_difference of [Passengers on capacity-tight route-months (threshold=0.85) — LAX — 2025-09…2026-07] , [Passengers on capacity-tight route-months (threshold=0.85) — SNA — 2025-09…2026-07]
- `runways_open`: count of open runways (OurAirports)
- `exploratory_sql`: column longest_runway_ft of: SELECT * FROM dim_airport WHERE oa_iata IN ('LAX','SNA')
- `ontime_coverage`: operated reporting-carrier departures (On-Time) / passenger departures (T-100), same window
- `intl_seat_share`: Σ seats on international segments / Σ seats

**Caveats and limitations**
- Scheduled peak from On-Time is a lower bound on total scheduled operations (reporting carriers only).
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- Exploratory SQL: definitions are not catalog metrics; verify before relying on it.
- Unmet demand, terminal capacity, fares, and profitability are not measured. Tight-capacity passenger share is the share of departing passengers on route-months above a seat-factor threshold. That seat factor is not, by itself, evidence of unmet demand.
- Geometric runway configuration — orientation, parallel versus intersecting layout, centerline separation, and independent arrival rates — is not available for this pair. Modeled hourly runway throughput is not a numeric finding for both airports, so the scheduled peak was not compared with a published acceptance rate.
- A peak per long runway is not defined for SNA because that count is 0 (exploratory query).
- Scheduled peak operations cover domestic flights of reporting carriers only and are a lower bound on total scheduled operations.
- Open-runway counts are a static snapshot and are not guaranteed to match the traffic window 2025-09…2026-07.
- This is a descriptive comparison of two airports in the same metro area. It is not an investment screen and not a valuation.