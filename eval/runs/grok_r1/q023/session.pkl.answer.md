## Victoria Regional (VCT) had the highest military operations share among towered Texas airports in FY2025

Among towered airports in Texas, military share of tower operations in FY2025 (2024-10…2025-09) is highest at Victoria Regional Airport (VCT), at 78.4% (calculated). In order after VCT, the next highest are Corpus Christi International Airport (CRP) at 50.8%, Rick Husband Amarillo International Airport (AMA) at 33.4%, Valley International Airport (HRL) at 31.0%, Abilene Regional Airport (ABI) at 20.5%, and Easterwood Field (CLL) at 16.8%. The next airport is El Paso International (ELP) at 9.6%. Every airport in the towered Texas set was scored; none were left out for missing data. These figures are a single-metric rank of a calculated share, not an investment screen and not a count of military operations.

**Findings and reasoning**
- *Fact*: Victoria Regional Airport (VCT) ranks first among towered Texas airports on military share of tower operations in FY2025, at 78.4% (calculated). [F34, F45]
- *Fact*: The next highest shares are Corpus Christi International (CRP) at 50.8%, Rick Husband Amarillo International (AMA) at 33.4%, Valley International (HRL) at 31.0%, Abilene Regional (ABI) at 20.5%, and Easterwood Field (CLL) at 16.8%. El Paso International (ELP) follows at 9.6%. [F11, F5, F22, F1, F9, F17]
- *Fact*: Each share is calculated as military operations / total tower operations over 2024-10…2025-09, from FAA ATADS tower counts. [F34]

**Assumptions**
- Towered Texas airports are the catalog group with state Texas and an ATADS tower record. No enplanement cutoff was applied.
- FY2025 is the window 2024-10…2025-09.
- The order is a within-set rank on military_ops_share alone, with higher share ranked higher.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F34 | Military share of tower operations — VCT — 2024-10…2025-09 | 78.4% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F11 | Military share of tower operations — CRP — 2024-10…2025-09 | 50.8% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F5 | Military share of tower operations — AMA — 2024-10…2025-09 | 33.4% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F22 | Military share of tower operations — HRL — 2024-10…2025-09 | 31.0% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F1 | Military share of tower operations — ABI — 2024-10…2025-09 | 20.5% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F9 | Military share of tower operations — CLL — 2024-10…2025-09 | 16.8% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F17 | Military share of tower operations — ELP — 2024-10…2025-09 | 9.6% | calculated | 2024-10…2025-09 | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |
| F45 | Ranking score — VCT | 100 | calculated | see inputs | faa_atads_ops [2024-10…2025-09 (12 periods)] |  |

**Methodology**
- `military_ops_share`: military operations / total tower operations
- `rank_score`: Σ weight × minmax_in_set-scaled criterion; criteria: military_ops_share (higher_better, w=1.0)

**Caveats and limitations**
- ATADS counts operations at towered airports during tower hours, all user classes.
- Scores are relative to the airports in this set; adding/removing airports changes them.
- ATADS counts operations at towered airports during tower hours only, for all user classes. Activity outside tower hours is not in the share.
- The result is a calculated share, not military-operation volume, unmet demand, terminal capacity, fares, or profitability. Those are not measured here.
- This is not an investment screen or a valuation, so there are no screening flags. Shares for VCT, CRP, AMA, HRL, ABI, CLL, and ELP all differ, so that order is not produced by a tie.
- Rank scores are relative to this set. Adding or removing airports would change them. Airports without an ATADS tower record are outside the comparison.