## Large hubs show no established link between top-carrier seat share and departure delay, and high-delay hubs are not concentration anomalies

Across FAA large hubs, largest operating-carrier seat share and departure delay rate were compared airport by airport for 2025-09…2026-07. The calculated Pearson correlation is -0.061. The calculated Spearman rank correlation is -0.072. The bootstrap interval for the Spearman correlation runs from -0.473 to 0.315 and uses 30 airports. That interval includes negative and positive values, so the sign of the rank association is not established. These figures are calculated associations across airports. They are not a forecast, and they do not show that carrier concentration causes delay.

High-delay hubs are the large hubs whose departure delay rate exceeds the upper-quartile benchmark 25.9% (P75 of dep_delay15_rate across set). Membership uses the full calculated rates, so a hub can remain in the set when its rendered percentage matches the benchmark. Those delay rates are FLL 30.3%, DFW 28.5%, BNA 28.4%, BWI 27.3%, DCA 26.9%, ORD 26.5%, MCO 26.0%, and LAS 25.9%. Top-carrier seat shares in that set are FLL 25.0%, DFW 66.1%, BNA 58.7%, BWI 74.9%, DCA 26.0%, ORD 37.0%, MCO 26.0%, and LAS 43.4%. The median top-carrier seat share in the high-delay set is 40.2%, the median across all large hubs is 43.9%, and the high-delay median minus the all-large-hub median is -3.7%.

Descriptive robust z-scores of seat share inside the high-delay set are FLL -0.70 MADs, DFW 1.19 MADs, BNA 0.85 MADs, BWI 1.59 MADs, DCA -0.65 MADs, ORD -0.15 MADs, MCO -0.65 MADs, and LAS 0.15 MADs. A cross-section anomaly screen at the catalog default robust-z threshold flagged no airport for top-carrier seat share inside that set. The same default screen flagged no large hub for departure delay rate and no large hub for top-carrier seat share. The z-scores above were recorded by retaining every hub in the set. They are calculated scores. The operator caveat that calls each an outlier relative to the set is not an anomaly flag. High delay in this answer is the upper-quartile cut, not a set of delay outliers.

**Findings and reasoning**
- *Fact*: For 2025-09…2026-07, the calculated Pearson correlation of top-carrier seat share and departure delay rate across large hubs is -0.061, the calculated Spearman rank correlation is -0.072, and the Spearman bootstrap interval runs from -0.473 to 0.315, using 30 airports. [F61, F62, F63, F64, F65, F99]
- *Inference*: The Spearman interval includes negative and positive values, so the sign of the rank association is not established. The result is a calculated cross-airport association and does not show that carrier concentration causes delay. [F61, F62, F63, F64]
- *Inference*: Large hubs whose departure delay rate exceeds the upper-quartile benchmark 25.9% (P75 of dep_delay15_rate across set) are FLL 30.3%, DFW 28.5%, BNA 28.4%, BWI 27.3%, DCA 26.9%, ORD 26.5%, MCO 26.0%, and LAS 25.9%. LAS stays in the set on the full calculated rate, which can render at the same percentage as the benchmark. [F99, F42, F39, F33, F35, F37, F53, F50, F47]
- *Fact*: Top-carrier seat shares in that high-delay set are FLL 25.0%, DFW 66.1%, BNA 58.7%, BWI 74.9%, DCA 26.0%, ORD 37.0%, MCO 26.0%, and LAS 43.4%. The high-delay median is 40.2%, the all-large-hub median is 43.9%, and the calculated gap is -3.7%. [F143, F142, F139, F140, F141, F146, F145, F144, F165, F200, F203]
- *Fact*: Descriptive robust z-scores of top-carrier seat share inside the high-delay set are FLL -0.70 MADs, DFW 1.19 MADs, BNA 0.85 MADs, BWI 1.59 MADs, DCA -0.65 MADs, ORD -0.15 MADs, MCO -0.65 MADs, and LAS 0.15 MADs. [F151, F150, F147, F148, F149, F154, F153, F152]
- *Inference*: The catalog default robust-z screen flagged no airport for top-carrier seat share inside the high-delay set, and it flagged no large hub for departure delay rate or for top-carrier seat share. The z-scores are descriptive scores from a screen that retains every hub in the set, not anomaly flags. High delay here is the upper-quartile cut rather than a delay-outlier set. [F151, F150, F147, F148, F149, F154, F153, F152, F99, F165, F200]
- *Hypothesis (not established by the data)*: Carrier concentration could still relate to delay through gates, schedules, or local operations, but this cross-section does not identify a cause. [F61, F62]

**Assumptions**
- Large hubs means the FAA large-hub class in the catalog group filter. The phrase large hubs did not resolve as a place name.
- High-delay means a large hub whose departure delay rate is above P75 of dep_delay15_rate across set during 2025-09…2026-07.
- Seat share and delay rate use that same window, the months covered by both T-100 seats and on-time departures.
- Descriptive robust z-scores retain every airport in the high-delay set. The anomaly test itself uses the catalog default threshold.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F99 | P75 of dep_delay15_rate across set | 25.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F61 | Pearson correlation: top_carrier_share vs dep_delay15_rate | -0.061 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F62 | Spearman rank correlation: top_carrier_share vs dep_delay15_rate | -0.072 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F63 | Spearman ρ 95% bootstrap CI, lower: top_carrier_share vs dep_delay15_rate | -0.473 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F64 | Spearman ρ 95% bootstrap CI, upper: top_carrier_share vs dep_delay15_rate | 0.315 | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F65 | airports used: top_carrier_share vs dep_delay15_rate | 30 airports | calculated | see inputs | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_ontime [2025-09…2026-07 (11 periods)] |  |
| F42 | Departure delay rate (≥15 min) — FLL — 2025-09…2026-07 | 30.3% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 77% (2025-09…2026-07) |
| F39 | Departure delay rate (≥15 min) — DFW — 2025-09…2026-07 | 28.5% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 87% (2025-09…2026-07) |
| F33 | Departure delay rate (≥15 min) — BNA — 2025-09…2026-07 | 28.4% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 93% (2025-09…2026-07) |
| F35 | Departure delay rate (≥15 min) — BWI — 2025-09…2026-07 | 27.3% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 95% (2025-09…2026-07) |
| F37 | Departure delay rate (≥15 min) — DCA — 2025-09…2026-07 | 26.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F53 | Departure delay rate (≥15 min) — ORD — 2025-09…2026-07 | 26.5% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 82% (2025-09…2026-07) |
| F50 | Departure delay rate (≥15 min) — MCO — 2025-09…2026-07 | 26.0% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 83% (2025-09…2026-07) |
| F47 | Departure delay rate (≥15 min) — LAS — 2025-09…2026-07 | 25.9% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 87% (2025-09…2026-07) |
| F143 | Largest operating carrier's seat share — FLL — 2025-09…2026-07 | 25.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F142 | Largest operating carrier's seat share — DFW — 2025-09…2026-07 | 66.1% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F139 | Largest operating carrier's seat share — BNA — 2025-09…2026-07 | 58.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F140 | Largest operating carrier's seat share — BWI — 2025-09…2026-07 | 74.9% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F141 | Largest operating carrier's seat share — DCA — 2025-09…2026-07 | 26.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F146 | Largest operating carrier's seat share — ORD — 2025-09…2026-07 | 37.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F145 | Largest operating carrier's seat share — MCO — 2025-09…2026-07 | 26.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F144 | Largest operating carrier's seat share — LAS — 2025-09…2026-07 | 43.4% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F165 | P50 of top_carrier_share across set | 40.2% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F200 | P50 of top_carrier_share across set | 43.9% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F203 | difference(F165, F200) | -3.7% | calculated | 2025-09…2026-07 | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)]; bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F151 | Robust z-score — top_carrier_share — FLL | -0.70 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F150 | Robust z-score — top_carrier_share — DFW | 1.19 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F147 | Robust z-score — top_carrier_share — BNA | 0.85 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F148 | Robust z-score — top_carrier_share — BWI | 1.59 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F149 | Robust z-score — top_carrier_share — DCA | -0.65 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F154 | Robust z-score — top_carrier_share — ORD | -0.15 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F153 | Robust z-score — top_carrier_share — MCO | -0.65 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F152 | Robust z-score — top_carrier_share — LAS | 0.15 MADs | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F66 | Departure delay rate (≥15 min) — ATL — 2025-09…2026-07 | 21.5% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 80% (2025-09…2026-07) |
| F67 | Departure delay rate (≥15 min) — AUS — 2025-09…2026-07 | 25.2% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 94% (2025-09…2026-07) |
| F68 | Departure delay rate (≥15 min) — BNA — 2025-09…2026-07 | 28.4% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 93% (2025-09…2026-07) |
| F69 | Departure delay rate (≥15 min) — BOS — 2025-09…2026-07 | 23.8% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 75% (2025-09…2026-07) |
| F70 | Departure delay rate (≥15 min) — BWI — 2025-09…2026-07 | 27.3% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 95% (2025-09…2026-07) |
| F71 | Departure delay rate (≥15 min) — CLT — 2025-09…2026-07 | 24.2% | calculated | 2025-09…2026-07 | bts_ontime [2025-09…2026-07 (11 periods)] | 71% (2025-09…2026-07) |
| F1 | Largest operating carrier's seat share — ATL — 2025-09…2026-07 | 73.3% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F2 | Largest operating carrier's seat share — AUS — 2025-09…2026-07 | 43.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F3 | Largest operating carrier's seat share — BNA — 2025-09…2026-07 | 58.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F4 | Largest operating carrier's seat share — BOS — 2025-09…2026-07 | 25.8% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F5 | Largest operating carrier's seat share — BWI — 2025-09…2026-07 | 74.9% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F6 | Largest operating carrier's seat share — CLT — 2025-09…2026-07 | 69.6% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F155 | Largest operating carrier's seat share — BNA — 2025-09…2026-07 | 58.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F156 | Largest operating carrier's seat share — BWI — 2025-09…2026-07 | 74.9% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F157 | Largest operating carrier's seat share — DCA — 2025-09…2026-07 | 26.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F158 | Largest operating carrier's seat share — DFW — 2025-09…2026-07 | 66.1% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F159 | Largest operating carrier's seat share — FLL — 2025-09…2026-07 | 25.0% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F160 | Largest operating carrier's seat share — LAS — 2025-09…2026-07 | 43.4% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F168 | Largest operating carrier's seat share — ATL — 2025-09…2026-07 | 73.3% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F169 | Largest operating carrier's seat share — AUS — 2025-09…2026-07 | 43.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F170 | Largest operating carrier's seat share — BNA — 2025-09…2026-07 | 58.7% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F171 | Largest operating carrier's seat share — BOS — 2025-09…2026-07 | 25.8% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F172 | Largest operating carrier's seat share — BWI — 2025-09…2026-07 | 74.9% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |
| F173 | Largest operating carrier's seat share — CLT — 2025-09…2026-07 | 69.6% | calculated | 2025-09…2026-07 | bts_t100_segment [2025-09…2026-07 (11 periods)] |  |

**Methodology**
- `quantile:dep_delay15_rate`: 75th percentile (linear interpolation) across 30 airports
- `pearson_r`: Pearson correlation of [top_carrier_share] and [dep_delay15_rate] across airports
- `spearman_rho`: Spearman rank correlation of [top_carrier_share] and [dep_delay15_rate] across airports
- `spearman_ci_low`: Spearman ρ 95% bootstrap CI, lower of [top_carrier_share] and [dep_delay15_rate] across airports
- `spearman_ci_high`: Spearman ρ 95% bootstrap CI, upper of [top_carrier_share] and [dep_delay15_rate] across airports
- `n`: airports used of [top_carrier_share] and [dep_delay15_rate] across airports
- `dep_delay15_rate`: departures ≥15 min late / operated departures
- `top_carrier_share`: max over operating carriers of seat share, departing passenger/combi segments
- `quantile:top_carrier_share`: 50th percentile (linear interpolation) across 8 airports
- `derived:difference`: difference of [P50 of top_carrier_share across set] , [P50 of top_carrier_share across set]
- `robust_z:top_carrier_share`: (value − median of set) / (1.4826·MAD), set of 8 airports

**Caveats and limitations**
- Association across airports, not causation; confounders (size, hub status, region) are not controlled.
- n = 30 airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ.
- On-Time covers domestic flights of reporting carriers only (no international, no small carriers).
- T-100 carriers are operating carriers; regional affiliates appear separately from their mainline partner.
- Outlier relative to this set; not necessarily an error or a problem.
- Departure delay rate covers domestic flights of reporting carriers only. Top-carrier seat share uses T-100 departing passenger and combi segments, including international flying, so the series do not describe the same traffic.
- The correlation does not control for airport size, region, season, or weather. It is not a forecast.
- No large hub met the default robust-z rule on delay rate, so high delay cannot be defined as a statistical delay outlier. The upper-quartile cut is an assumption.
- The concentration test inside the high-delay set compares each hub with the other hubs in that set. A separate default screen of top-carrier seat share on all large hubs also returned no flags.
- The default screen emits a finding only for a flagged airport, so an empty screen is the operator result rather than a stored count of anomalies.
- On-time coverage runs through August 2026, while T-100 seats in this extract end in July 2026. The shared window stops where both series exist.
- Unmet demand, terminal capacity, fares, and profitability are not measured. This is not an investment screen and not a valuation.