## ANC T12 freight is concentrated on freighters, which slightly outnumber passenger departures

Over 2025-08…2026-07, Ted Stevens Anchorage International (ANC) enplaned 5,705.15M lbs of freight (observed). Passenger departures were 40,425 departures (observed). Departures of all aircraft configurations were 86,971 departures (observed).

Freight pounds and passenger departures use different units, so the levels are not a like-for-like volume ranking. The calculated intensity is 141129.331 pounds of freight enplaned per passenger departure (5,705.15M lbs divided by 40,425 departures). That result is calculated from observed totals. It is not a specialization index, a forecast, or a valuation.

On a common unit, freight-configured departures were 46,546 departures (observed), compared with passenger departures of 40,425 departures. Freight-configured departures exceeded passenger departures by 6,121 departures (calculated). The ratio of freight-configured departures to passenger departures is 1.151 (calculated). The ratio of freight-configured departures to all departures is 0.535 (calculated); the ratio of passenger departures to all departures is 0.465 (calculated).

The service-type split reconciles to those totals. Passenger-configured departures were 39,546 departures and combi departures were 879 departures. Their sum is 40,425 departures, and the difference from passenger departures is 0 departures (calculated). Adding freight-configured departures gives 86,971 departures, and the difference from all departures is 0 departures (calculated). The T12 departure total is therefore fully accounted for by freight, passenger, and combi configurations.

Freight pounds by configuration, all observed: freight-configured aircraft 5,550.84M lbs, passenger-configured aircraft 133.42M lbs, and combi aircraft 20.90M lbs. Calculated shares of total freight enplaned are 0.973, 0.023, and 0.004. Those three shares sum to 1.000.

Within ANC over this window, dedicated freighter flying is the larger departure category and carries nearly all of the freight. Passenger departures remain large, and only a small share of freight moves on passenger aircraft. This describes the cargo-versus-passenger mix at ANC. It is not an investment screen, not a peer rank, and not evidence of unmet demand, facility capacity, fares, or profitability.

**Findings and reasoning**
- *Fact*: Over 2025-08…2026-07, ANC enplaned 5,705.15M lbs of freight (observed). Passenger departures were 40,425 departures (observed). Departures of all configurations were 86,971 departures (observed). [F1, F2, F3]
- *Fact*: Freight-configured departures were 46,546 departures, passenger-configured departures were 39,546 departures, and combi departures were 879 departures. Passenger-configured plus combi departures sum to 40,425 departures, differing from passenger departures by 0 departures. All three configuration rows sum to 86,971 departures, differing from all departures by 0 departures. [F8, F9, F7, F18, F20, F19, F21]
- *Fact*: Freight pounds were 5,550.84M lbs on freight-configured aircraft, 133.42M lbs on passenger-configured aircraft, and 20.90M lbs on combi aircraft, all observed. [F5, F6, F4]
- *Fact*: Calculated comparisons are 141129.331 pounds of freight per passenger departure, a ratio of freight-configured departures to passenger departures of 1.151, a ratio of freight-configured departures to all departures of 0.535, a ratio of passenger departures to all departures of 0.465, and an excess of freight-configured over passenger departures of 6,121 departures. [F10, F11, F12, F13, F16]
- *Fact*: Calculated shares of freight pounds are 0.973 on freight-configured aircraft, 0.023 on passenger-configured aircraft, and 0.004 on combi aircraft, summing to 1.000. [F14, F15, F17, F22]
- *Inference*: Relative to its own passenger departures over this window, ANC has a cargo-weighted operating mix: freighter departures outnumber passenger departures (ratio 1.151, excess 6,121 departures, ratio to all departures 0.535), and nearly all enplaned freight is on freighter aircraft (ratio 0.973) rather than on passenger aircraft (ratio 0.023). The departure tilt is modest; the tonnage concentration on freighters is strong. [F11, F16, F12, F14, F15, F8, F2, F5]
- *Hypothesis (not established by the data)*: Why freighters dominate ANC freight — network role, geography, or carrier strategy — is not identified by these metrics. Any such cause remains a hypothesis.

**Assumptions**
- Anchorage (ANC) is bound to Ted Stevens Anchorage International Airport. Merrill Field and the Anchorage CBSA as a group are excluded because the question names ANC.
- Passenger departures follow the catalog definition: performed departures of passenger, combi, and seaplane aircraft. In this window that total matches passenger-configured plus combi departures (difference 0 departures).
- Freight-configured departures are the service-type freight slice of all departures. Cargo-versus-passenger specialization is read from that within-airport mix and from where freight pounds sit, not from a peer ranking or an investment screen.
- The cross-unit comparison is freight pounds divided by passenger departures and is interpreted as pounds of freight per passenger departure.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Freight enplaned — ANC — 2025-08…2026-07 | 5,705.15M lbs | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F2 | Passenger departures — ANC — 2025-08…2026-07 | 40,425 departures | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F3 | All departures (incl. cargo) — ANC — 2025-08…2026-07 | 86,971 departures | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F10 | ratio(F1, F2) | 141129.331 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F8 | All departures (incl. cargo) — service_type=freight — 2025-08…2026-07 | 46,546 departures | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F16 | difference(F8, F2) | 6,121 departures | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F11 | ratio(F8, F2) | 1.151 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F12 | ratio(F8, F3) | 0.535 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F13 | ratio(F2, F3) | 0.465 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F9 | All departures (incl. cargo) — service_type=passenger — 2025-08…2026-07 | 39,546 departures | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F7 | All departures (incl. cargo) — service_type=combi — 2025-08…2026-07 | 879 departures | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F18 | sum(F9, F7) | 40,425 departures | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F20 | difference(F18, F2) | 0 departures | calculated | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F19 | sum(F8, F9, F7) | 86,971 departures | calculated | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F21 | difference(F19, F3) | 0 departures | calculated | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F5 | Freight enplaned — service_type=freight — 2025-08…2026-07 | 5,550.84M lbs | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F6 | Freight enplaned — service_type=passenger — 2025-08…2026-07 | 133.42M lbs | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F4 | Freight enplaned — service_type=combi — 2025-08…2026-07 | 20.90M lbs | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F14 | ratio(F5, F1) | 0.973 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F15 | ratio(F6, F1) | 0.023 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F17 | ratio(F4, F1) | 0.004 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F22 | sum(F14, F15, F17) | 1.000 | calculated | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |

**Methodology**
- `freight_lbs`: Σ freight on departing segments
- `departures`: Σ departures performed, passenger/combi aircraft
- `all_departures`: Σ departures performed, all aircraft configurations
- `derived:ratio`: ratio of [Freight enplaned — ANC — 2025-08…2026-07] , [Passenger departures — ANC — 2025-08…2026-07]
- `derived:difference`: difference of [All departures (incl. cargo) — service_type=freight — 2025-08…2026-07] , [Passenger departures — ANC — 2025-08…2026-07]
- `derived:sum`: sum of [All departures (incl. cargo) — service_type=passenger — 2025-08…2026-07] , [All departures (incl. cargo) — service_type=combi — 2025-08…2026-07]

**Caveats and limitations**
- Unmet demand, terminal or cargo-facility capacity, fares, and profitability are not measured, so this mix does not establish them.
- No cross-airport rank or screen was run. Whether ANC is more cargo-specialized than other US airports is not established.
- Freight enplaned excludes mail. It is segment freight on departing T-100 flights, not cargo revenue and not ton-miles.
- FAA hub class for ANC is a passenger-enplanement classification and does not measure cargo specialization.
- Ratios and differences are calculated from observed T12 totals. They are not forecasts or estimates.
- A ratio of pounds to departures is an intensity. It does not mean freight activity is economically larger than passenger activity.