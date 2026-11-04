## Passenger long-haul share at ANC is 6.1% (2025-08…2026-07)

Over 2025-08…2026-07, the calculated share of passenger traffic departing Ted Stevens Anchorage International (ANC) on long-haul segments is 6.1%. The definition is share of departing passengers on segments ≥ 3000 statute miles, scope = passenger. Observed passenger-scope enplanements in that window are 2.78M passengers, and observed seats offered on that same passenger scope are 3.80M seats. The catalog cannot weight long-haul share by seats, so 3.80M seats describes capacity offered, not a second proportion.

Scheduled service is not a filter on the catalog metric. An exploratory cut to BTS class F on passenger aircraft gives the ratio 0.062 (exploratory query), long-haul passengers 166,414 (exploratory query) divided by scheduled passenger enplanements 2.70M (exploratory query). The renderer shows that exploratory result as a ratio, on the same zero-to-one scale as the catalog share, which is shown as a percent. That scheduled slice is 0.971 (exploratory query) of observed passenger-scope enplanements 2.78M passengers. Scheduled combi passengers are 561 (exploratory query), and that row returned no long-haul passenger total. Class G passenger-aircraft passengers are 0 (exploratory query).

The proportion moves sharply with the distance cutoff. The calculated passenger-scope share is 30.3% under share of departing passengers on segments ≥ 2000 statute miles, scope = passenger and 0.4% under share of departing passengers on segments ≥ 3500 statute miles, scope = passenger. The exploratory scheduled-class ratios at those cutoffs are 0.311 (exploratory query) and 0.003 (exploratory query).

A share of flights is a different quantity. The calculated passenger-scope departure share is 4.4%, using share of departing departures on segments ≥ 3000 statute miles, scope = passenger. The exploratory share among scheduled class F passenger departures is 0.027 (exploratory query), from 1,005 (exploratory query) of 37,092 (exploratory query).

Cargo is not part of the passenger result. At the catalog default cutoff, the calculated long-haul share of freight tonnage is 63.5% and of freight departures is 51.5%. Across all configurations the departure share is 29.6%.

**Findings and reasoning**
- *Fact*: Over 2025-08…2026-07, the calculated long-haul share of departing passenger traffic at ANC is 6.1%, defined as share of departing passengers on segments ≥ 3000 statute miles, scope = passenger. Observed passenger-scope enplanements are 2.78M passengers and observed seats offered are 3.80M seats. [F1, F7, F9]
- *Fact*: Restricting to BTS scheduled class F on passenger aircraft, the exploratory long-haul passenger ratio is 0.062 (exploratory query), from 166,414 (exploratory query) over 2.70M (exploratory query). That scheduled slice is 0.971 (exploratory query) of passenger-scope enplanements. [F63, F11, F10, F67, F7]
- *Fact*: At the other catalog cutoffs, the calculated passenger-scope shares are 30.3% (share of departing passengers on segments ≥ 2000 statute miles, scope = passenger) and 0.4% (share of departing passengers on segments ≥ 3500 statute miles, scope = passenger). The exploratory scheduled-class ratios are 0.311 (exploratory query) and 0.003 (exploratory query). [F3, F4, F64, F65]
- *Fact*: Weighted by departures, the calculated passenger-scope long-haul share is 4.4%. The exploratory scheduled class F passenger departure share is 0.027 (exploratory query), from 1,005 (exploratory query) over 37,092 (exploratory query). [F2, F66, F15, F14]
- *Fact*: Freight and all-configuration shares at the catalog default cutoff are 63.5% for freight tonnage, 51.5% for freight departures, and 29.6% for all departures. These are not the passenger-traffic proportion. [F60, F61, F62]
- *Inference*: For passenger traffic in this window, the catalog share 6.1% is a close reading of scheduled class F traffic because that class is 0.971 (exploratory query) of passenger-scope enplanements and the exploratory scheduled ratio is 0.062 (exploratory query). The departure-weighted shares 4.4% and 0.027 (exploratory query) answer a different question and are lower. [F1, F63, F67, F2, F66]

**Assumptions**
- ANC is Ted Stevens Anchorage International Airport. Merrill Field is a separate Anchorage airport and is excluded.
- The question names no period, so every catalog figure uses the trailing T12 of departing T-100 segments, 2025-08…2026-07.
- Long-haul means the catalog default in share of departing passengers on segments ≥ 3000 statute miles, scope = passenger. The question does not set a distance cutoff, so the other catalog cutoffs are reported beside it.
- Passenger traffic means enplaned passengers, so the primary weight is passengers. Departure-weighted figures are a separate reading of the share of flights.
- Scheduled is not a catalog parameter. The exploratory cut keeps BTS service class F on passenger-configured aircraft. The catalog passenger scope also includes non-scheduled service plus combi and seaplane configurations.
- Out of means segments departing ANC, not arrivals.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Long-haul share (min_miles=3000, scope=passenger, weight=passengers) — ANC — 2025-08…2026-07 | 6.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F7 | Enplaned passengers — ANC — 2025-08…2026-07 | 2.78M passengers | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F9 | Seats offered — ANC — 2025-08…2026-07 | 3.80M seats | observed | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F63 | ratio(F11, F10) | 0.062 (exploratory query) | exploratory | as queried | as queried | bts_t100_segment [n/a]; bts_t100_segment [n/a] |  |
| F11 | pax_ge_3000 (exploratory query) | 166,414 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F10 | passengers (exploratory query) | 2.70M (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F67 | ratio(F10, F7) | 0.971 (exploratory query) | exploratory | as queried | 2025-08…2026-07 | bts_t100_segment [n/a]; bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F24 | passengers (exploratory query) | 561 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F50 | passengers (exploratory query) | 0 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F3 | Long-haul share (min_miles=2000, scope=passenger, weight=passengers) — ANC — 2025-08…2026-07 | 30.3% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F4 | Long-haul share (min_miles=3500, scope=passenger, weight=passengers) — ANC — 2025-08…2026-07 | 0.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F64 | ratio(F12, F10) | 0.311 (exploratory query) | exploratory | as queried | as queried | bts_t100_segment [n/a]; bts_t100_segment [n/a] |  |
| F65 | ratio(F13, F10) | 0.003 (exploratory query) | exploratory | as queried | as queried | bts_t100_segment [n/a]; bts_t100_segment [n/a] |  |
| F2 | Long-haul share (min_miles=3000, scope=passenger, weight=departures) — ANC — 2025-08…2026-07 | 4.4% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F66 | ratio(F15, F14) | 0.027 (exploratory query) | exploratory | as queried | as queried | bts_t100_segment [n/a]; bts_t100_segment [n/a] |  |
| F15 | dep_ge_3000 (exploratory query) | 1,005 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F14 | departures (exploratory query) | 37,092 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F60 | Long-haul share (min_miles=3000, scope=freight, weight=freight) — ANC — 2025-08…2026-07 | 63.5% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F61 | Long-haul share (min_miles=3000, scope=freight, weight=departures) — ANC — 2025-08…2026-07 | 51.5% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F62 | Long-haul share (min_miles=3000, scope=all, weight=departures) — ANC — 2025-08…2026-07 | 29.6% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F12 | pax_ge_2000 (exploratory query) | 840,039 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |
| F13 | pax_ge_3500 (exploratory query) | 8,546 (exploratory query) | exploratory | as queried | bts_t100_segment [n/a] |  |

**Methodology**
- `long_haul_share(min_miles=3000,scope=passenger,weight=passengers)`: share of departing passengers on segments ≥ 3000 statute miles, scope = passenger
- `passengers`: Σ passengers on departing passenger/combi segments
- `seats`: Σ seats on departing passenger/combi segments
- `derived:ratio`: ratio of [pax_ge_3000 (exploratory query)] , [passengers (exploratory query)]
- `exploratory_sql`: column pax_ge_3000 of: SELECT service_type, is_scheduled, class, SUM(passengers) AS passengers, SUM(passengers) FILTER (WHERE distance >= 3000) AS pax_ge_3000, SUM(passengers) FILTER (WHERE distance >= 2000) AS pax_ge_2000, SUM(passengers) FILTER (WHERE distance >= 3500) AS pax_ge_3500, SUM(departures_performed) AS departures, SUM(departures_performed) FILTER (WHERE distance >= 3000) AS dep_ge_3000 FROM v_t100_segment WHERE origin_airport_id = 10299 AND period_month >= DATE '2025-08-01' AND period_month <= DATE '2026-07-01' GROUP BY service_type, is_scheduled, class ORDER BY passengers DESC
- `long_haul_share(min_miles=2000,scope=passenger,weight=passengers)`: share of departing passengers on segments ≥ 2000 statute miles, scope = passenger
- `long_haul_share(min_miles=3500,scope=passenger,weight=passengers)`: share of departing passengers on segments ≥ 3500 statute miles, scope = passenger
- `long_haul_share(min_miles=3000,scope=passenger,weight=departures)`: share of departing departures on segments ≥ 3000 statute miles, scope = passenger
- `long_haul_share(min_miles=3000,scope=freight,weight=freight)`: share of departing freight on segments ≥ 3000 statute miles, scope = freight
- `long_haul_share(min_miles=3000,scope=freight,weight=departures)`: share of departing departures on segments ≥ 3000 statute miles, scope = freight
- `long_haul_share(min_miles=3000,scope=all,weight=departures)`: share of departing departures on segments ≥ 3000 statute miles, scope = all

**Caveats and limitations**
- T-100 passengers are segment enplanements (connecting passengers count at each enplanement).
- Exploratory SQL: definitions are not catalog metrics; verify before relying on it.
- Figures are performed segment enplanements, including connections, not a forward published schedule and not origin-destination journeys. A long segment is not the same thing as a long passenger itinerary.
- Scheduled combi passengers are 561 (exploratory query), with no long-haul passenger total returned for that row. Class G passenger-aircraft passengers are 0 (exploratory query).
- Exploratory ratios are not catalog metrics.
- Cargo long-haul shares 63.5% and 51.5%, and the all-configuration departure share 29.6%, describe a different operation and are not the passenger result.
- The cutoff is a parameter. 30.3% and 0.4% show that another catalog cutoff changes the passenger proportion by a wide margin.
- Unmet demand, terminal capacity, fares, and profitability are not measured by this data.