## CY 2024 home-CBSA per-capita income and passenger seat factor have a positive calculated association across South Atlantic commercial-service airports, and the rank interval includes no association

Across commercial-service airports in the Census South Atlantic division, the calculated Pearson correlation of home-CBSA per-capita income with passenger seat factor is 0.123. The calculated Spearman rank correlation is 0.135. The paired sample is 62 airports.

The calculated Spearman bootstrap interval runs from -0.131 to 0.399. The lower end is negative and the upper end is positive, so the interval includes no rank association.

Income is a calculated series: BEA personal income / population of the home CBSA, window CY2024. Passenger seat factor is a calculated series: Σ passengers / Σ seats, departing passenger/combi segments, window 2024-01…2024-12. Those wording placeholders point at the ABY input rows Home-CBSA per-capita income — ABY — CY2024 and Seat factor — ABY — 2024-01…2024-12. They are not a division total.

**Findings and reasoning**
- *Fact*: The Pearson correlation of CY 2024 home-CBSA per-capita income with passenger seat factor is 0.123, calculated. The Spearman rank correlation is 0.135, calculated. The paired sample is 62 airports. [F126, F127, F130]
- *Fact*: The Spearman bootstrap interval is -0.131 to 0.399, calculated. [F128, F129]
- *Fact*: Income in this correlation is BEA personal income / population of the home CBSA over CY2024, calculated. Passenger seat factor is Σ passengers / Σ seats, departing passenger/combi segments over 2024-01…2024-12, calculated. [F1, F63]
- *Inference*: A reliable association is not established. The Spearman interval includes a negative value and a positive value, so it is consistent with no rank association and with a positive association. The positive point estimates alone do not show that higher-income metros have higher seat factors. [F126, F127, F128, F129]

**Assumptions**
- South Atlantic means the Census South Atlantic division. The place name resolves to that division exactly.
- Commercial service means airports in that division at or above the resolver commercial-service enplanement floor. Airports below that floor are excluded, including smaller commercial-service airports.
- Income and seat factor are both taken on CY 2024, the latest year with home-CBSA income and a complete calendar year of seat factor. Later seat-factor months are left out because income coverage ends in CY 2024.
- Each airport is one observation. Airports that share a home CBSA are kept separate.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F126 | Pearson correlation: cbsa_per_capita_income vs seat_factor | 0.123 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F127 | Spearman rank correlation: cbsa_per_capita_income vs seat_factor | 0.135 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F130 | airports used: cbsa_per_capita_income vs seat_factor | 62 airports | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F128 | Spearman ρ 95% bootstrap CI, lower: cbsa_per_capita_income vs seat_factor | -0.131 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F129 | Spearman ρ 95% bootstrap CI, upper: cbsa_per_capita_income vs seat_factor | 0.399 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F1 | Home-CBSA per-capita income — ABY — CY2024 | $50,619 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F63 | Seat factor — ABY — 2024-01…2024-12 | 55.4% | calculated | 2024-01…2024-12 | bts_t100_segment [2024-01…2024-12 (12 periods)] |  |
| F2 | Home-CBSA per-capita income — AGS — CY2024 | $54,106 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F3 | Home-CBSA per-capita income — ATL — CY2024 | $71,365 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F4 | Home-CBSA per-capita income — AVL — CY2024 | $67,592 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F5 | Home-CBSA per-capita income — BQK — CY2024 | $61,562 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F6 | Home-CBSA per-capita income — BWI — CY2024 | $81,133 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |

**Methodology**
- `pearson_r`: Pearson correlation of [cbsa_per_capita_income] and [seat_factor] across airports
- `spearman_rho`: Spearman rank correlation of [cbsa_per_capita_income] and [seat_factor] across airports
- `n`: airports used of [cbsa_per_capita_income] and [seat_factor] across airports
- `spearman_ci_low`: Spearman ρ 95% bootstrap CI, lower of [cbsa_per_capita_income] and [seat_factor] across airports
- `spearman_ci_high`: Spearman ρ 95% bootstrap CI, upper of [cbsa_per_capita_income] and [seat_factor] across airports
- `cbsa_per_capita_income`: BEA personal income / population of the home CBSA
- `seat_factor`: Σ passengers / Σ seats, departing passenger/combi segments

**Caveats and limitations**
- Association across airports, not causation; confounders (size, hub status, region) are not controlled.
- n = 62 airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ.
- Home CBSA is an administrative proxy for the market area, not a measured catchment.
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- This is an association across airports. It does not hold size, hub status, or carrier mix fixed, and it is not a cause, a valuation, or a screening rank.
- Home-CBSA income is an administrative proxy for the market area, not a measured catchment. Airports in one metro repeat one income value, so the points are not independent metros.
- RBN is in the screened set and absent from the paired sample. An exploratory airport-to-CBSA crosswalk returns no home-CBSA title for RBN. That crosswalk result is exploratory, not a catalog metric.
- Passenger seat factor does not measure unmet demand, terminal capacity, fares, or profitability.
- The rank interval still contains a positive association, so the data also do not establish that income and seat factor are unrelated.