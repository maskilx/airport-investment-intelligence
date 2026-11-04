## Boston Logan screens highest for expansion among scored New England airports under the base scenario; the screen does not measure terminal capacity.

Among New England census-division airports that clear the base scenario enplanement gate, Boston Logan International (BOS) has the highest expansion screen score at 69.34. Next are Portland International Jetport (PWM, Maine) at 47.08 and Tweed New Haven (HVN) at 45.12. The screen flags Tweed as tied with Portland. Those scores are separate findings, so the tie flag does not mean the scores are equal. Bradley International (BDL) at 41.92 is not flagged as tied with Tweed. T. F. Green (PVD) at 40.80 is flagged as tied with Bradley. Manchester-Boston Regional (MHT) at 38.48 is flagged as tied with T. F. Green. Patrick Leahy Burlington International (BTV) at 36.10 is flagged as tied with Manchester-Boston. Portland Jetport is not flagged as tied with Boston Logan, and Bradley is not flagged as tied with Tweed.

Each score is calculated. The base score combines an unconstrained FAA TAF enplanement change (forecast), realized passenger growth (calculated), and home-CBSA per-capita income (calculated). Logan inputs are forecast change 5.61M enplanements (FAA forecast), realized growth -2.3%, and income $104,104. Portland inputs are 278,078 enplanements (FAA forecast), 0.7%, and $82,962. Tweed inputs are 138,599 enplanements (FAA forecast), 3.6%, and $73,967. Bradley inputs are 523,236 enplanements (FAA forecast), -4.3%, and $83,411. T. F. Green inputs are 348,264 enplanements (FAA forecast), -1.3%, and $70,086. Manchester-Boston inputs are 114,449 enplanements (FAA forecast), -0.0%, and $80,473. Burlington inputs are 163,754 enplanements (FAA forecast), -1.8%, and $76,064. The TAF change is an FAA forecast, not observed traffic and not unmet demand.

Every scored airport is flagged AIRFIELD_UNKNOWN because no verified FAA capacity rate is on file. The screen therefore does not establish an airfield constraint or a terminal constraint. Tweed is also flagged CARRIER_CONCENTRATION on a calculated largest-carrier seat share of 87.0%.

Boston Logan stays first under the equal-weights, demand-only, and momentum-heavy scenarios reported with this screen. The order below Logan does not. Under demand-only, Bradley and T. F. Green rank above Portland. Under momentum-heavy, Tweed ranks above Portland.

Airports below the base gate were not scored. Bangor International (437,108 enplanements) is the first airport the screen lists below that gate. A further set of New England airports has no FAA enplanement record and was not scored.

**Findings and reasoning**
- *Fact*: Under the base expansion screen, Boston Logan calculated score 69.34 is the highest among New England airports the model scored, followed by Portland Jetport 47.08, Tweed New Haven 45.12, Bradley 41.92, T. F. Green 40.80, Manchester-Boston 38.48, and Burlington 36.10. [F94, F95, F96, F97, F98, F99, F100]
- *Fact*: The screen flags Tweed as tied with Portland, T. F. Green as tied with Bradley, Manchester-Boston as tied with T. F. Green, and Burlington as tied with Manchester-Boston. Portland Jetport is not flagged as tied with Boston Logan, and Bradley is not flagged as tied with Tweed. [F94, F95, F96, F97, F98, F99, F100]
- *Fact*: Logan score inputs are the FAA TAF enplanement change 5.61M enplanements (FAA forecast) (forecast), realized passenger growth -2.3% (calculated), and home-CBSA per-capita income $104,104 (calculated). The same input types are 278,078 enplanements (FAA forecast), 0.7%, and $82,962 for Portland; 138,599 enplanements (FAA forecast), 3.6%, and $73,967 for Tweed; 523,236 enplanements (FAA forecast), -4.3%, and $83,411 for Bradley; 348,264 enplanements (FAA forecast), -1.3%, and $70,086 for T. F. Green; 114,449 enplanements (FAA forecast), -0.0%, and $80,473 for Manchester-Boston; and 163,754 enplanements (FAA forecast), -1.8%, and $76,064 for Burlington. [F34, F55, F67, F44, F65, F72, F38, F59, F69, F32, F53, F66, F42, F63, F71, F40, F61, F70, F36, F57, F68]
- *Fact*: Every scored airport carries an AIRFIELD_UNKNOWN flag because no verified FAA capacity rate is available. Tweed also carries a CARRIER_CONCENTRATION flag based on largest-carrier seat share 87.0%. [F94, F95, F96, F97, F98, F99, F100, F76]
- *Fact*: In the equal-weights, demand-only, and momentum-heavy scenarios reported with this screen, Boston Logan remains first. Under demand-only, Bradley and T. F. Green rank above Portland. Under momentum-heavy, Tweed ranks above Portland. [F94, F95, F96, F97, F98]
- *Fact*: Bangor International, with enplanements 437,108 enplanements, is the first airport the screen lists as below the base scenario enplanement gate and was not scored. [F4]
- *Inference*: A high base screen score does not establish that terminal expansion is the indicated project. The score ranks expansion opportunity from forecast passenger growth, recent traffic growth, and market income. It does not measure terminal capacity, unmet demand, fares, or profitability, and the missing capacity rate means a terminal constraint is not established. [F94, F34, F55, F67]

**Assumptions**
- New England is the Census division of that name, the group the entity resolver returned.
- The base screening scenario is the catalog scenario named base. The scenario enplanement gate was left as specified and was not lowered to pull smaller commercial airports into the ranking.
- Portland in this result is Portland International Jetport in Maine, the New England airport the screen scored.
- Commercial airports the base screen can rank are those that clear the gate. Airports below the gate, and airports with no FAA enplanement record, are outside the scored set rather than assigned a low rank.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F94 | Expansion screen score — BOS (base) | 69.34 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F95 | Expansion screen score — PWM (base) | 47.08 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F96 | Expansion screen score — HVN (base) | 45.12 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F97 | Expansion screen score — BDL (base) | 41.92 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F98 | Expansion screen score — PVD (base) | 40.80 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F99 | Expansion screen score — MHT (base) | 38.48 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F100 | Expansion screen score — BTV (base) | 36.10 | calculated | see inputs | faa_taf [2025]; faa_taf [2025]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)]; bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F34 | FAA TAF enplanements change — BOS — FY2035 vs FY2025 | 5.61M enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F55 | Enplaned passengers change (%) — BOS — 2025-08…2026-07 vs 2024-08…2025-07 | -2.3% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F67 | Home-CBSA per-capita income — BOS — CY2024 | $104,104 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F44 | FAA TAF enplanements change — PWM — FY2035 vs FY2025 | 278,078 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F65 | Enplaned passengers change (%) — PWM — 2025-08…2026-07 vs 2024-08…2025-07 | 0.7% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F72 | Home-CBSA per-capita income — PWM — CY2024 | $82,962 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F38 | FAA TAF enplanements change — HVN — FY2035 vs FY2025 | 138,599 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F59 | Enplaned passengers change (%) — HVN — 2025-08…2026-07 vs 2024-08…2025-07 | 3.6% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F69 | Home-CBSA per-capita income — HVN — CY2024 | $73,967 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F32 | FAA TAF enplanements change — BDL — FY2035 vs FY2025 | 523,236 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F53 | Enplaned passengers change (%) — BDL — 2025-08…2026-07 vs 2024-08…2025-07 | -4.3% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F66 | Home-CBSA per-capita income — BDL — CY2024 | $83,411 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F42 | FAA TAF enplanements change — PVD — FY2035 vs FY2025 | 348,264 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F63 | Enplaned passengers change (%) — PVD — 2025-08…2026-07 vs 2024-08…2025-07 | -1.3% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F71 | Home-CBSA per-capita income — PVD — CY2024 | $70,086 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F40 | FAA TAF enplanements change — MHT — FY2035 vs FY2025 | 114,449 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F61 | Enplaned passengers change (%) — MHT — 2025-08…2026-07 vs 2024-08…2025-07 | -0.0% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F70 | Home-CBSA per-capita income — MHT — CY2024 | $80,473 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F36 | FAA TAF enplanements change — BTV — FY2035 vs FY2025 | 163,754 enplanements (FAA forecast) | forecast | FY2035 vs FY2025 | faa_taf [2025]; faa_taf [2025] |  |
| F57 | Enplaned passengers change (%) — BTV — 2025-08…2026-07 vs 2024-08…2025-07 | -1.8% | calculated | 2025-08…2026-07 vs 2024-08…2025-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F68 | Home-CBSA per-capita income — BTV — CY2024 | $76,064 | calculated | CY2024 | bea_cainc1 [latest-release]; census_cbsa [2023]; faa_nasr_apt [2026-10-29] |  |
| F76 | Largest operating carrier's seat share — HVN — 2025-08…2026-07 | 87.0% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F4 | FAA CY enplanements (ACAIS) — BGR — CY2025 | 437,108 enplanements | observed | CY2025 | faa_enplanements [2012…2025 (10 periods)] |  |
| F25 | FAA TAF enplanements — BOS — FY2035 | 26.81M enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F33 | FAA TAF enplanements — BOS — FY2025 | 21.20M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F46 | Enplaned passengers — BOS — 2025-08…2026-07 | 20.95M passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F54 | Enplaned passengers — BOS — 2024-08…2025-07 | 21.45M passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F30 | FAA TAF enplanements — PWM — FY2035 | 1.56M enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F43 | FAA TAF enplanements — PWM — FY2025 | 1.29M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F51 | Enplaned passengers — PWM — 2025-08…2026-07 | 1.28M passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F64 | Enplaned passengers — PWM — 2024-08…2025-07 | 1.27M passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F27 | FAA TAF enplanements — HVN — FY2035 | 859,973 enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F37 | FAA TAF enplanements — HVN — FY2025 | 721,374 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F48 | Enplaned passengers — HVN — 2025-08…2026-07 | 729,373 passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F58 | Enplaned passengers — HVN — 2024-08…2025-07 | 704,106 passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F24 | FAA TAF enplanements — BDL — FY2035 | 3.85M enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F31 | FAA TAF enplanements — BDL — FY2025 | 3.33M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F45 | Enplaned passengers — BDL — 2025-08…2026-07 | 3.21M passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F52 | Enplaned passengers — BDL — 2024-08…2025-07 | 3.35M passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F29 | FAA TAF enplanements — PVD — FY2035 | 2.46M enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F41 | FAA TAF enplanements — PVD — FY2025 | 2.11M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F50 | Enplaned passengers — PVD — 2025-08…2026-07 | 2.07M passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F62 | Enplaned passengers — PVD — 2024-08…2025-07 | 2.10M passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F28 | FAA TAF enplanements — MHT — FY2035 | 787,190 enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F39 | FAA TAF enplanements — MHT — FY2025 | 672,741 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F49 | Enplaned passengers — MHT — 2025-08…2026-07 | 667,630 passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F60 | Enplaned passengers — MHT — 2024-08…2025-07 | 667,886 passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |
| F26 | FAA TAF enplanements — BTV — FY2035 | 877,725 enplanements (FAA forecast) | forecast | FY2035 | faa_taf [2025] |  |
| F35 | FAA TAF enplanements — BTV — FY2025 | 713,971 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F47 | Enplaned passengers — BTV — 2025-08…2026-07 | 700,664 passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F56 | Enplaned passengers — BTV — 2024-08…2025-07 | 713,850 passengers | observed | 2024-08…2025-07 | bts_t100_segment [2024-08…2025-07 (12 periods)] |  |

**Methodology**
- `screen_score:1.0`: Σ weight × anchored score of: Projected passenger increase (FAA TAF FY2025→FY2035, absolute) [10000→10000000, log10] w=0.5; Realized passenger growth (T-100, trailing 12 months vs prior 12) [-0.05→0.1, linear] w=0.3; Home-CBSA per-capita income (latest BEA year) [45000→110000, linear] w=0.2
- `abs_change:taf_enplanements`: change of [FAA Terminal Area Forecast total enplanements (domestic + international)]: FY2035 vs FY2025
- `pct_change:passengers`: change (%) of [Σ passengers on departing passenger/combi segments]: 2025-08…2026-07 vs 2024-08…2025-07
- `cbsa_per_capita_income`: BEA personal income / population of the home CBSA
- `top_carrier_share`: max over operating carriers of seat share, departing passenger/combi segments
- `acais_enplanements`: FAA official calendar-year revenue passenger boardings
- `taf_enplanements`: FAA Terminal Area Forecast total enplanements (domestic + international)
- `passengers`: Σ passengers on departing passenger/combi segments

**Caveats and limitations**
- Screening rank of expansion opportunity, not a financial valuation: no costs, debt, airline-agreement economics or construction risk are modelled.
- TAF component is an FAA forecast (unconstrained).
- FAA TAF values for forecast years are FAA's unconstrained forecast, not observations.
- Federal fiscal year (Oct–Sep).
- T-100 passengers are segment enplanements (connecting passengers count at each enplanement).
- Home CBSA is an administrative proxy for the market area, not a measured catchment.
- T-100 carriers are operating carriers; regional affiliates appear separately from their mainline partner.
- This is a screening rank of expansion opportunity, not a valuation. Costs, debt, airline-agreement economics, and construction risk are not modelled.
- The passenger-increase component is an unconstrained FAA TAF forecast, not observed traffic and not unmet demand.
- Terminal capacity, gate capacity, fares, and profitability are not measured. NPIAS development need and recent FAA grants shown beside the screen are estimated or observed context only. They are not score inputs and they do not identify a terminal project.
- AIRFIELD_UNKNOWN on every scored airport means no verified FAA capacity rate is available, so neither an airfield constraint nor a terminal constraint is established.
- Tie flags come from the model. Flagged airports do not have identical scores.
- Rank order below Boston Logan changes under the other scenarios the screen reports, so the base order is not robust behind Logan.
- Smaller commercial airports in New England were not scored. Bangor is one excluded airport that has an FAA enplanement record. Many other New England fields have no FAA enplanement record and were not scored either.