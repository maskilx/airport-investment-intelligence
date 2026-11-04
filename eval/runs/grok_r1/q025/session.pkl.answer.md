## Among small-hub airports, CY2024 home-CBSA population and CY2025 ACAIS enplanements have a weak linear correlation (0.089) and a positive rank correlation (0.527).

For FAA small-hub airports (hub class S) with both series, the calculated Pearson correlation is 0.089 and the calculated Spearman rank correlation is 0.527. The Spearman bootstrap interval runs from 0.316 to 0.683. The correlation uses 77 airports. Home-CBSA population is the observed BEA figure for CY2024. CY2025 population is out of coverage. ACAIS enplanements are the observed FAA calendar-year boardings for CY2025.

**Findings and reasoning**
- *Fact*: The calculated Pearson correlation between home-CBSA population and CY2025 ACAIS enplanements is 0.089. [F157]
- *Fact*: The calculated Spearman rank correlation is 0.527, with a bootstrap interval from 0.316 to 0.683. [F158, F159, F160]
- *Fact*: The correlation is calculated on 77 airports with both a CY2024 home-CBSA population and CY2025 ACAIS enplanements. [F161]
- *Fact*: GUM and STT have CY2025 ACAIS enplanements of 966,278 enplanements and 802,734 enplanements and no home CBSA, so they are outside the correlation. [F162, F163]
- *Inference*: The linear association is weak, while the rank association is positive and its bootstrap interval lies entirely on the positive side. Across these airports, a larger home-CBSA population tends to coincide with higher enplanements in rank, but not in proportion. [F157, F158, F159, F160]
- *Hypothesis (not established by the data)*: Small-hub status already groups airports by enplanement scale, and some airports share a home CBSA. Either pattern could mute a straight-line correlation while leaving the ranks aligned. This calculation does not identify that mechanism. [F157, F158]

**Assumptions**
- Small hub means FAA hub class S, the latest ACAIS hub class stored for each airport.
- CY2025 home-CBSA population is out of coverage for area_cbsa, whose latest year is CY2024. The correlation pairs observed CY2024 population with observed CY2025 ACAIS enplanements.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F157 | Pearson correlation: cbsa_population vs acais_enplanements | 0.089 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_enplanements [2012…2025 (10 periods)] |  |
| F158 | Spearman rank correlation: cbsa_population vs acais_enplanements | 0.527 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_enplanements [2012…2025 (10 periods)] |  |
| F159 | Spearman ρ 95% bootstrap CI, lower: cbsa_population vs acais_enplanements | 0.316 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_enplanements [2012…2025 (10 periods)] |  |
| F160 | Spearman ρ 95% bootstrap CI, upper: cbsa_population vs acais_enplanements | 0.683 | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_enplanements [2012…2025 (10 periods)] |  |
| F161 | airports used: cbsa_population vs acais_enplanements | 77 airports | calculated | see inputs | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29]; faa_enplanements [2012…2025 (10 periods)] |  |
| F162 | FAA CY enplanements (ACAIS) — GUM — CY2025 | 966,278 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F163 | FAA CY enplanements (ACAIS) — STT — CY2025 | 802,734 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F1 | Home-CBSA population — ALB — CY2024 | 913,485 persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F2 | Home-CBSA population — ATW — CY2024 | 248,992 persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F3 | Home-CBSA population — AVL — CY2024 | 422,333 persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F4 | Home-CBSA population — AZA — CY2024 | 5.19M persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F5 | Home-CBSA population — BHM — CY2024 | 1.19M persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F6 | Home-CBSA population — BIL — CY2024 | 192,531 persons | observed | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |

**Methodology**
- `pearson_r`: Pearson correlation of [cbsa_population] and [acais_enplanements] across airports
- `spearman_rho`: Spearman rank correlation of [cbsa_population] and [acais_enplanements] across airports
- `spearman_ci_low`: Spearman ρ 95% bootstrap CI, lower of [cbsa_population] and [acais_enplanements] across airports
- `spearman_ci_high`: Spearman ρ 95% bootstrap CI, upper of [cbsa_population] and [acais_enplanements] across airports
- `n`: airports used of [cbsa_population] and [acais_enplanements] across airports
- `acais_enplanements`: FAA official calendar-year revenue passenger boardings
- `cbsa_population`: BEA population of the airport's home CBSA (distinct areas summed for groups)

**Caveats and limitations**
- Association across airports, not causation; confounders (size, hub status, region) are not controlled.
- n = 77 airports; bootstrap CI (1,000 resamples, seed 0) on Spearman ρ.
- Home CBSA is an administrative proxy for the market area, not a measured catchment.
- Area-level value (home CBSA/county): airports or groups sharing an area repeat the same value; never add these across rows.
- This is an association across airports, not a cause, a catchment study, or a valuation. Unmet demand, terminal capacity, fares, and profitability are not measured.
- Home CBSA is an administrative proxy for the market area, not a measured catchment. Airports that share a CBSA carry the same population, and each airport remains a separate observation.
- The bootstrap interval applies to the Spearman coefficient. No interval is reported for the Pearson coefficient.
- The result applies only inside the small-hub class.