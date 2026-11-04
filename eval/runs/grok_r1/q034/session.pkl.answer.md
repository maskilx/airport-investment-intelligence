## Highest tight-capacity passenger shares in CY2025, with taxi-out and busiest hour where On-Time exists

US airports at or above the commercial enplanement floor, ordered by calculated tight-capacity passenger share in CY2025 (2025-01…2025-12). Definition: share of departing passengers on route-months with passengers/seats ≥ 0.85. This is a metric rank, not an investment screen, so screening flags do not apply.

1. STC — 82.4%
2. PVU — 76.6%
3. RFD — 76.0%
4. EAT — 73.6%
5. LNK — 72.4%
6. SJU — 66.4%
7. ERI — 64.6%
8. BQN — 63.3%
9. LCK — 62.6%
10. AZA — 62.1%

AZA 75.42 outranks SGF 74.94 on this same rank, and the shares 62.1% and 61.7% are not equal, so the cutoff is not a tie.

Average taxi-out and busiest scheduled hour cannot be established for full CY2025. On-Time coverage starts after the beginning of that year. The measures below use 2025-09…2025-12 only.

The flight-weighted average taxi-out for the ranked airports that have On-Time taxi-out observations, excluding EAT, is 15.2 min (calculated) over 2025-09…2025-12. It is total taxi-out minutes divided by flights with taxi-out, not an equal-weight mean of the airport figures. On-Time coverage for that group total is below the coverage threshold.

EAT has no On-Time rows in 2025-09…2025-12, so average taxi-out and busiest scheduled hour are not established for EAT.

Busiest scheduled hour is non-additive across airports, so there is no set total. Airport-level values are below. Taxi-out is calculated. Busiest hour is observed.

1. STC — taxi-out 11.5 min; busiest hour 2 operations/hour
2. PVU — taxi-out 18.7 min; busiest hour 4 operations/hour
3. RFD — taxi-out 13.5 min; busiest hour 2 operations/hour
4. EAT — taxi-out and busiest hour not established
5. LNK — taxi-out 22.8 min; busiest hour 3 operations/hour
6. SJU — taxi-out 14.5 min; busiest hour 26 operations/hour
7. ERI — taxi-out 16.3 min; busiest hour 2 operations/hour
8. BQN — taxi-out 12.9 min; busiest hour 3 operations/hour
9. LCK — taxi-out 13.3 min; busiest hour 3 operations/hour
10. AZA — taxi-out 14.5 min; busiest hour 10 operations/hour

ERI 16.3 min, PVU 18.7 min, and SJU 14.5 min are flagged for low On-Time coverage, so taxi-out at those airports describes a partial slice. The same flag is on busiest hour for ERI 2 operations/hour, PVU 4 operations/hour, and SJU 26 operations/hour.

**Findings and reasoning**
- *Fact*: In CY2025 (2025-01…2025-12), calculated tight-capacity passenger share is 82.4% at STC, 76.6% at PVU, 76.0% at RFD, 73.6% at EAT, 72.4% at LNK, 66.4% at SJU, 64.6% at ERI, 63.3% at BQN, 62.6% at LCK, and 62.1% at AZA. [F370, F314, F322, F119, F228, F358, F127, F59, F220, F32]
- *Fact*: AZA 75.42 outranks SGF 74.94, and share 62.1% is not equal to share 61.7%, so the cutoff is not a tie. [F422, F423, F32, F350]
- *Fact*: Flight-weighted average taxi-out for the ranked airports with On-Time taxi-out observations, excluding EAT, is 15.2 min (calculated) in 2025-09…2025-12. [F796]
- *Fact*: STC taxi-out is 11.5 min and busiest scheduled hour is 2 operations/hour.
PVU taxi-out is 18.7 min and busiest scheduled hour is 4 operations/hour.
RFD taxi-out is 13.5 min and busiest scheduled hour is 2 operations/hour.
LNK taxi-out is 22.8 min and busiest scheduled hour is 3 operations/hour.
SJU taxi-out is 14.5 min and busiest scheduled hour is 26 operations/hour.
ERI taxi-out is 16.3 min and busiest scheduled hour is 2 operations/hour.
BQN taxi-out is 12.9 min and busiest scheduled hour is 3 operations/hour.
LCK taxi-out is 13.3 min and busiest scheduled hour is 3 operations/hour.
AZA taxi-out is 14.5 min and busiest scheduled hour is 10 operations/hour. [F786, F795, F783, F792, F784, F793, F782, F791, F785, F794, F780, F789, F779, F788, F781, F790, F778, F787]
- *Inference*: Because busiest scheduled hour is defined airport by airport, the airport-level figures are the aggregate of peak hour scheduled operations. A set total is not a meaningful reading of that metric. [F795, F792, F793, F791, F794, F789, F788, F790, F787]
- *Hypothesis (not established by the data)*: A high tight-capacity passenger share may come from scheduling on a thin set of routes. That cause is not established, and the share does not measure unmet demand, terminal capacity, or profitability. [F370]

**Assumptions**
- The rank covers US airports whose latest calendar-year enplanements meet the commercial floor used for this entity set. Airports under that floor are outside the order.
- Tight-capacity passenger share uses the catalog default threshold in share of departing passengers on route-months with passengers/seats ≥ 0.85. A stricter threshold was not applied.
- Higher share ranks higher. The rank tool also stores a set-relative min-max score. That score is not a valuation and would change if the airport set changed.
- Peak hour scheduled operations is read as busiest scheduled hour: the maximum, over date and local hour, of scheduled arrivals plus departures on reporting-carrier operated flights. The percentile form of scheduled peak is not used.
- Taxi-out and busiest hour are limited to On-Time months inside CY2025 (2025-09…2025-12), because a full CY2025 window is out of coverage for On-Time.
- The pooled taxi-out leaves out EAT, which has no On-Time rows in that window.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F370 | Passengers on capacity-tight route-months (threshold=0.85) — STC — 2025-01…2025-12 | 82.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F314 | Passengers on capacity-tight route-months (threshold=0.85) — PVU — 2025-01…2025-12 | 76.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F322 | Passengers on capacity-tight route-months (threshold=0.85) — RFD — 2025-01…2025-12 | 76.0% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F119 | Passengers on capacity-tight route-months (threshold=0.85) — EAT — 2025-01…2025-12 | 73.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F228 | Passengers on capacity-tight route-months (threshold=0.85) — LNK — 2025-01…2025-12 | 72.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F358 | Passengers on capacity-tight route-months (threshold=0.85) — SJU — 2025-01…2025-12 | 66.4% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F127 | Passengers on capacity-tight route-months (threshold=0.85) — ERI — 2025-01…2025-12 | 64.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F59 | Passengers on capacity-tight route-months (threshold=0.85) — BQN — 2025-01…2025-12 | 63.3% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F220 | Passengers on capacity-tight route-months (threshold=0.85) — LCK — 2025-01…2025-12 | 62.6% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F32 | Passengers on capacity-tight route-months (threshold=0.85) — AZA — 2025-01…2025-12 | 62.1% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F422 | Ranking score — AZA | 75.42 | calculated | see inputs | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F423 | Ranking score — SGF | 74.94 | calculated | see inputs | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F350 | Passengers on capacity-tight route-months (threshold=0.85) — SGF — 2025-01…2025-12 | 61.7% | calculated | 2025-01…2025-12 | bts_t100_segment [2025-01…2025-12 (12 periods)] |  |
| F796 | Average taxi-out — group total — 2025-09…2025-12 | 15.2 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 64% (2025-09…2025-12) |
| F778 | Average taxi-out — AZA — 2025-09…2025-12 | 14.5 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 93% (2025-09…2025-12) |
| F787 | Busiest scheduled hour — AZA — 2025-09…2025-12 | 10 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 93% (2025-09…2025-12) |
| F786 | Average taxi-out — STC — 2025-09…2025-12 | 11.5 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 80% (2025-09…2025-12) |
| F795 | Busiest scheduled hour — STC — 2025-09…2025-12 | 2 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 80% (2025-09…2025-12) |
| F783 | Average taxi-out — PVU — 2025-09…2025-12 | 18.7 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 57% (2025-09…2025-12) |
| F792 | Busiest scheduled hour — PVU — 2025-09…2025-12 | 4 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 57% (2025-09…2025-12) |
| F784 | Average taxi-out — RFD — 2025-09…2025-12 | 13.5 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 92% (2025-09…2025-12) |
| F793 | Busiest scheduled hour — RFD — 2025-09…2025-12 | 2 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 92% (2025-09…2025-12) |
| F782 | Average taxi-out — LNK — 2025-09…2025-12 | 22.8 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 95% (2025-09…2025-12) |
| F791 | Busiest scheduled hour — LNK — 2025-09…2025-12 | 3 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 95% (2025-09…2025-12) |
| F785 | Average taxi-out — SJU — 2025-09…2025-12 | 14.5 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 57% (2025-09…2025-12) |
| F794 | Busiest scheduled hour — SJU — 2025-09…2025-12 | 26 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 57% (2025-09…2025-12) |
| F780 | Average taxi-out — ERI — 2025-09…2025-12 | 16.3 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 9% (2025-09…2025-12) |
| F789 | Busiest scheduled hour — ERI — 2025-09…2025-12 | 2 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 9% (2025-09…2025-12) |
| F779 | Average taxi-out — BQN — 2025-09…2025-12 | 12.9 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 100% (2025-09…2025-12) |
| F788 | Busiest scheduled hour — BQN — 2025-09…2025-12 | 3 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 100% (2025-09…2025-12) |
| F781 | Average taxi-out — LCK — 2025-09…2025-12 | 13.3 min | calculated | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 98% (2025-09…2025-12) |
| F790 | Busiest scheduled hour — LCK — 2025-09…2025-12 | 3 operations/hour | observed | 2025-09…2025-12 | bts_ontime [2025-09…2025-12 (4 periods)] | 98% (2025-09…2025-12) |

**Methodology**
- `tight_capacity_pax_share(threshold=0.85)`: share of departing passengers on route-months with passengers/seats ≥ 0.85
- `rank_score`: Σ weight × minmax_in_set-scaled criterion; criteria: tight_capacity_pax_share(threshold=0.85) (higher_better, w=1.0)
- `avg_taxi_out_min`: Σ taxi-out minutes / flights with taxi-out
- `peak_hour_ops_max`: maximum over (date, local hour) of scheduled arrivals+departures, reporting carriers, operated flights

**Caveats and limitations**
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- Scores are relative to the airports in this set; adding/removing airports changes them.
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- On-Time covers less than 70% of this airport's airline departures; delay/peak figures describe a partial slice.
- Scheduled peak from On-Time is a lower bound on total scheduled operations (reporting carriers only).
- Full CY2025 average taxi-out and busiest scheduled hour are not established. On-Time data do not cover the early months of CY2025.
- EAT has no On-Time observations in the covered months, so taxi-out and busiest hour are missing for EAT.
- ERI, PVU, and SJU, plus the group taxi-out total, sit below the On-Time coverage threshold. Those figures describe reporting-carrier domestic flights, and a partial slice where the low-coverage flag applies.
- Busiest scheduled hour is a lower bound from reporting carriers and cannot be added across airports.
- The group taxi-out is flight-weighted. It will not match an equal-weight mean of the airport-level taxi-out figures.
- Tight-capacity passenger share does not measure unmet demand, terminal capacity, fares, or profitability.
- Some airports above the enplanement floor had no computed share and were not scored. They are absent from this order.
- This is not the investment screening model, so screening flags and the screen tie band do not apply. Here a tie would mean equal shares, and the cutoff shares are not equal.