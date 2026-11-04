## FY2024 TAF enplanement forecasts cannot be scored for medium hubs

The names medium hub and medium_hub do not resolve to a city, airport, or region. The set used here is FAA hub class M.

A forecast-versus-actual comparison of enplanements for FY2024 is not applicable. In the loaded TAF release, FY2024 is historical, so there is no forecast left to exceed. The hub class M TAF enplanement figure for that year is 172.00M enplanements (observed). FAA TAF enplanements — record_type=historical — FY2024.

T-100 passengers, the actual side of that comparison, do not cover FY2024. Coverage starts in January 2024, and the fiscal year starts in October 2023, so October, November, and December 2023 are outside the series.

No airport in this group can be classified as over, under, or in line with a FY2024 TAF enplanement forecast. A grant trend limited to airports that beat that forecast is not established.

The grant path below is the full hub class M group, unfiltered. Observed FAA grants awarded are $1.56B (FAA grants awarded — fiscal_year=2021 — FY2021–2025), $966.0M (FAA grants awarded — fiscal_year=2022 — FY2021–2025), $735.1M (FAA grants awarded — fiscal_year=2023 — FY2021–2025), $863.6M (FAA grants awarded — fiscal_year=2024 — FY2021–2025), and $1.04B (FAA grants awarded — fiscal_year=2025 — FY2021–2025). Calculated change versus the prior fiscal year is -38.1%, then -23.9%, then 17.5%, then 20.7%. FY2025 versus FY2021 is -33.2%. The group-total CAGR is -9.6% (calculated; FAA grants awarded CAGR over 4 years — group total — FY2025 vs FY2021).

Equal-weight airport CAGRs over the same span have a low decile of -29.2%, a lower quartile of -16.4%, a median of -7.7%, an upper quartile of 2.9%, and a high decile of 13.4%. 50th percentile (linear interpolation) across 34 airports.

SMF does not enter that percentile set. Observed awards at SMF are $22.3M (FAA grants awarded — fiscal_year=2021 — FY2021–2025), $70.9M (FAA grants awarded — fiscal_year=2022 — FY2021–2025), $11.7M (FAA grants awarded — fiscal_year=2023 — FY2021–2025), and $21.3M (FAA grants awarded — fiscal_year=2024 — FY2021–2025). No FY2025 grants_awarded_usd finding was returned for SMF, so a CAGR is undefined.

The monthly trend operator does not apply: grant amounts are fiscal-year figures and cannot be grouped by month. The fiscal-year series above is the trend that this catalog can compute.

**Findings and reasoning**
- *Fact*: For hub class M in FY2024, FAA TAF enplanements are 172.00M enplanements, class observed, described by FAA TAF enplanements — record_type=historical — FY2024. [F1]
- *Fact*: Observed FAA grants awarded for the full hub class M group are $1.56B, $966.0M, $735.1M, $863.6M, and $1.04B. Calculated changes versus the prior fiscal year are -38.1%, -23.9%, 17.5%, and 20.7%. FY2025 versus FY2021 is -33.2%, and the group-total CAGR is -9.6%. [F2, F3, F4, F5, F6, F223, F224, F225, F226, F227, F111]
- *Fact*: Across airports with a defined grant CAGR, the equal-weight distribution is a low decile of -29.2%, a lower quartile of -16.4%, a median of -7.7%, an upper quartile of 2.9%, and a high decile of 13.4%. 50th percentile (linear interpolation) across 34 airports. [F214, F215, F216, F217, F218]
- *Fact*: At SMF, observed FAA grants awarded are $22.3M, $70.9M, $11.7M, and $21.3M. [F219, F220, F221, F222]
- *Inference*: The signs of -38.1% and -23.9%, then 17.5% and 20.7%, describe a group award total that falls from FY2021 to FY2023 and rises from FY2023 to FY2025. -33.2% and -9.6% show that the FY2025 group total is still under the FY2021 total. The median airport CAGR is -7.7%. None of these calculations identifies airports that beat a FY2024 enplanement forecast. [F223, F224, F225, F226, F227, F111, F216]
- *Hypothesis (not established by the data)*: The grant path may reflect the mix and timing of award programs rather than a change in modernization need. That cause is not identified here. The path is not evidence of unmet demand, terminal capacity, fares, or profitability. [F2, F111]

**Assumptions**
- Medium hub means the stored FAA hub class M. The phrases medium hub and medium_hub did not match a city, airport, or region.
- Exceeded a FY2024 TAF enplanement forecast would mean T-100 passenger enplanements above the TAF enplanement figure for that same fiscal year. That comparison is defined for forecast years in the loaded release.
- Grant totals and the group CAGR cover every airport in hub class M. They are not limited to airports that beat a FY2024 forecast, because that subset is not established.
- Group totals sum awarded dollars. Airports with no returned award in a year add nothing to that year. The CAGR percentiles weight each airport with a defined CAGR equally and are not dollar-weighted.
- A missing FY2025 grants_awarded_usd row for SMF means no value was returned. It is not a recorded award amount.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | FAA TAF enplanements — record_type=historical — FY2024 | 172.00M enplanements | observed | FY2024 | faa_taf [2025] |  |
| F2 | FAA grants awarded — fiscal_year=2021 — FY2021–2025 | $1.56B | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F3 | FAA grants awarded — fiscal_year=2022 — FY2021–2025 | $966.0M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F4 | FAA grants awarded — fiscal_year=2023 — FY2021–2025 | $735.1M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F5 | FAA grants awarded — fiscal_year=2024 — FY2021–2025 | $863.6M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F6 | FAA grants awarded — fiscal_year=2025 — FY2021–2025 | $1.04B | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F223 | pct_difference(F3, F2) | -38.1% | calculated | FY2021–2025 | FY2021–2025 | faa_grants [2021…2025 (5 periods)]; faa_grants [2021…2025 (5 periods)] |  |
| F224 | pct_difference(F4, F3) | -23.9% | calculated | FY2021–2025 | FY2021–2025 | faa_grants [2021…2025 (5 periods)]; faa_grants [2021…2025 (5 periods)] |  |
| F225 | pct_difference(F5, F4) | 17.5% | calculated | FY2021–2025 | FY2021–2025 | faa_grants [2021…2025 (5 periods)]; faa_grants [2021…2025 (5 periods)] |  |
| F226 | pct_difference(F6, F5) | 20.7% | calculated | FY2021–2025 | FY2021–2025 | faa_grants [2021…2025 (5 periods)]; faa_grants [2021…2025 (5 periods)] |  |
| F227 | pct_difference(F6, F2) | -33.2% | calculated | FY2021–2025 | FY2021–2025 | faa_grants [2021…2025 (5 periods)]; faa_grants [2021…2025 (5 periods)] |  |
| F111 | FAA grants awarded CAGR over 4 years — group total — FY2025 vs FY2021 | -9.6% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F214 | P10 of cagr:grants_awarded_usd across set | -29.2% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F215 | P25 of cagr:grants_awarded_usd across set | -16.4% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F216 | P50 of cagr:grants_awarded_usd across set | -7.7% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F217 | P75 of cagr:grants_awarded_usd across set | 2.9% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F218 | P90 of cagr:grants_awarded_usd across set | 13.4% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F219 | FAA grants awarded — fiscal_year=2021 — FY2021–2025 | $22.3M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F220 | FAA grants awarded — fiscal_year=2022 — FY2021–2025 | $70.9M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F221 | FAA grants awarded — fiscal_year=2023 — FY2021–2025 | $11.7M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F222 | FAA grants awarded — fiscal_year=2024 — FY2021–2025 | $21.3M | observed | FY2021–2025 | faa_grants [2021…2025 (5 periods)] |  |
| F109 | FAA grants awarded — group total — FY2025 | $1.04B | observed | FY2025 | faa_grants [2025] |  |
| F110 | FAA grants awarded — group total — FY2021 | $1.56B | observed | FY2021 | faa_grants [2021] |  |
| F147 | FAA grants awarded CAGR over 4 years — ABQ — FY2025 vs FY2021 | -43.0% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F149 | FAA grants awarded CAGR over 4 years — ANC — FY2025 vs FY2021 | -4.6% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F151 | FAA grants awarded CAGR over 4 years — BDL — FY2025 vs FY2021 | -16.5% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F153 | FAA grants awarded CAGR over 4 years — BOI — FY2025 vs FY2021 | 1.5% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F155 | FAA grants awarded CAGR over 4 years — BUF — FY2025 vs FY2021 | 15.3% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |
| F157 | FAA grants awarded CAGR over 4 years — BUR — FY2025 vs FY2021 | -4.4% | calculated | FY2025 vs FY2021 | faa_grants [2025]; faa_grants [2021] |  |

**Methodology**
- `taf_enplanements`: FAA Terminal Area Forecast total enplanements (domestic + international)
- `grants_awarded_usd`: Σ awarded FAA grant totals (award date present)
- `derived:pct_difference`: pct_difference of [FAA grants awarded — fiscal_year=2022 — FY2021–2025] , [FAA grants awarded — fiscal_year=2021 — FY2021–2025]
- `cagr:grants_awarded_usd`: CAGR over 4 years of [Σ awarded FAA grant totals (award date present)]: FY2025 vs FY2021
- `quantile:cagr:grants_awarded_usd`: 10th percentile (linear interpolation) across 34 airports

**Caveats and limitations**
- Federal fiscal year (Oct–Sep).
- Awarded grant dollars at award date; not spending or project completion.
- Which medium hubs exceeded TAF enplanement forecasts in FY2024 cannot be established. The TAF year is historical, and T-100 passengers miss the opening months of FY2024.
- In a year where forecast_vs_actual does run, the actual enplanement side is T-100 segment passengers, while TAF history is built on a different enplanement definition. ACAIS calendar-year boardings were not used as a substitute.
- Awarded grant dollars are recorded at the award date. They are not expenditures, project completion, or a funding commitment beyond the award.
- Unmet demand, terminal capacity, fares, and profitability are not measured.
- This is not an investment screen and not a valuation. No screen scenario, flags, or tie list was produced.
- A monthly trend is not defined for fiscal-year grants. Hub class is the stored FAA class and was not recomputed from FY2024 enplanements.