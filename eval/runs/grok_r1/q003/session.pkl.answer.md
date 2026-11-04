## In the on-time months of CY2025, SNA had the higher departure delay rate and LAX had the longer average taxi-out

A full CY2025 comparison is not available. On-time departures do not cover January through August 2025, and the calendar-year window was out of coverage. The figures below are calculated for 2025-09…2025-12 only, the part of CY2025 inside on-time coverage.

Departure delay rate (departures ≥15 min late / operated departures) was 19.2% at Los Angeles International (LAX) and 20.0% at John Wayne Orange County (SNA). Both are calculated. LAX minus SNA is -0.9%. As a percent difference relative to SNA, the LAX rate is -4.3%.

Average taxi-out was 18.4 min at LAX and 16.2 min at SNA, also calculated. LAX minus SNA is 2.2 min. As a percent difference relative to SNA, the LAX average is 13.4%.

On-time coverage of airline departures in the same window was 73.2% at LAX and 88.1% at SNA. These delay and taxi-out results describe domestic flights of reporting carriers, not every departure at either airport.

**Findings and reasoning**
- *Fact*: For 2025-09…2025-12, the LAX departure delay rate was 19.2% (calculated) and the SNA rate was 20.0% (calculated). [F1, F2]
- *Fact*: The LAX-minus-SNA difference in departure delay rate is -0.9% (calculated). The percent difference of the LAX rate relative to SNA is -4.3%. [F5, F7]
- *Fact*: For 2025-09…2025-12, average taxi-out was 18.4 min at LAX and 16.2 min at SNA, both calculated. [F3, F4]
- *Fact*: The LAX-minus-SNA difference in average taxi-out is 2.2 min. The percent difference of the LAX average relative to SNA is 13.4%. [F6, F8]
- *Fact*: On-time coverage of airline departures was 73.2% at LAX and 88.1% at SNA over 2025-09…2025-12. [F9, F10]
- *Inference*: Within this partial window, covered SNA departures were delayed at a higher rate than covered LAX departures, while covered LAX departures had the longer average taxi-out. In relative terms versus SNA, the taxi-out gap (13.4%) is larger in magnitude than the delay-rate gap (-4.3%). [F5, F6, F7, F8]

**Assumptions**
- Los Angeles International (LAX) is Los Angeles International Airport in Los Angeles, CA.
- Santa Ana John Wayne (SNA) is bound to John Wayne Orange County International Airport in Santa Ana, CA. The combined name did not resolve; the code SNA and the city Santa Ana each resolved to that single airport. This contrast is answered under that binding.
- The requested period is CY2025. Because that window is not fully covered by on-time departures, the comparison uses 2025-09…2025-12 only.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Departure delay rate (≥15 min) — LAX — 2025-09…2025-12 | 19.2% | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 73% (2025-09…2025-12) |
| F2 | Departure delay rate (≥15 min) — SNA — 2025-09…2025-12 | 20.0% | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 88% (2025-09…2025-12) |
| F5 | difference(F1, F2) | -0.9% | calculated | 2025-09…2025-12 | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_ontime [2025-09…2025-12 (4 periods)] |  |
| F7 | pct_difference(F1, F2) | -4.3% | calculated | 2025-09…2025-12 | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_ontime [2025-09…2025-12 (4 periods)] |  |
| F3 | Average taxi-out — LAX — 2025-09…2025-12 | 18.4 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 73% (2025-09…2025-12) |
| F4 | Average taxi-out — SNA — 2025-09…2025-12 | 16.2 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 88% (2025-09…2025-12) |
| F6 | difference(F3, F4) | 2.2 min | calculated | 2025-09…2025-12 | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_ontime [2025-09…2025-12 (4 periods)] |  |
| F8 | pct_difference(F3, F4) | 13.4% | calculated | 2025-09…2025-12 | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_ontime [2025-09…2025-12 (4 periods)] |  |
| F9 | On-Time coverage of airline departures — LAX — 2025-09…2025-12 | 73.2% | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_t100_segment [2025-09…2025-12 (4 periods)] | 73% (2025-09…2025-12) |
| F10 | On-Time coverage of airline departures — SNA — 2025-09…2025-12 | 88.1% | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)]; bts_t100_segment [2025-09…2025-12 (4 periods)] | 88% (2025-09…2025-12) |

**Methodology**
- `dep_delay15_rate`: departures ≥15 min late / operated departures
- `derived:difference`: difference of [Departure delay rate (≥15 min) — LAX — 2025-09…2025-12] , [Departure delay rate (≥15 min) — SNA — 2025-09…2025-12]
- `derived:pct_difference`: pct_difference of [Departure delay rate (≥15 min) — LAX — 2025-09…2025-12] , [Departure delay rate (≥15 min) — SNA — 2025-09…2025-12]
- `avg_taxi_out_min`: Σ taxi-out minutes / flights with taxi-out
- `ontime_coverage`: operated reporting-carrier departures (On-Time) / passenger departures (T-100), same window

**Caveats and limitations**
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- Full CY2025 departure delay rate and average taxi-out cannot be established. On-time departures in this catalog run from September 2025 through August 2026. January through August 2025 are outside coverage. Months in 2026 fall outside the requested year and were not included.
- On-time metrics cover domestic flights of reporting carriers only. International flights and smaller carriers are excluded. Coverage of airline departures differs between the airports (73.2% at LAX, 88.1% at SNA), so the comparison is not airport-wide and the measured shares are not equal.
- The rate difference -0.9% uses the same display as the rates. The percent differences -4.3% and 13.4% are LAX relative to SNA.
- Unmet demand, terminal capacity, fares, and profitability are not measured. No cause of either gap is established by these data.