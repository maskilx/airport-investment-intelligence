## Miami International Airport Load Factors and Terminal Investment Evaluation

The observed seat factor for Miami International Airport is 81.1%, and the distance-weighted segment load factor is 83.7%. Passenger load factors measure airline flight seat utilization and do not prove that a terminal expansion will yield a financial return on investment. Unmet demand, terminal capacity, airfares, and profitability are not directly measured by this data. Consequently, operational traffic data cannot verify project returns or determine whether bondholders should finance terminal expansion.

**Findings and reasoning**
- *Fact*: Miami International Airport recorded a calculated seat factor of 81.1% and a distance-weighted segment load factor of 83.7%. [F1, F2]
- *Inference*: High flight seat occupancy reflects airline capacity utilization rather than physical terminal constraints or unmet demand. [F1, F2]
- *Hypothesis (not established by the data)*: A specific financial return on investment and bondholder financing feasibility cannot be validated from flight utilization metrics because financial returns, project costs, and terminal capacity are unmeasured. [F1, F2]

**Assumptions**
- Operating metrics from recent scheduled passenger traffic reflect recent utilization at Miami International Airport.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F1 | Seat factor — MIA — 2025-08…2026-07 | 81.1% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |
| F2 | Distance-weighted load factor — MIA — 2025-08…2026-07 | 83.7% | calculated | 2025-08…2026-07 | bts_t100_segment [2025-08…2026-07 (12 periods)] |  |

**Methodology**
- `seat_factor`: Σ passengers / Σ seats, departing passenger/combi segments
- `segment_load_factor`: Σ(passengers·distance) / Σ(seats·distance), departing segments (not system RPM/ASM)

**Caveats and limitations**
- Seat factor varies little across large airports and is not, by itself, evidence of unmet demand.
- Unmet demand, terminal capacity, fares, and profitability are not directly measured by this data.
- Financial return on investment, debt service coverage, and project costs are outside the scope of the available operational catalog.