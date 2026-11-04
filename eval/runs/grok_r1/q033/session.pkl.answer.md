## CLT has the largest absolute gap between observed CY2025 ACAIS enplanements and the FY2025 TAF projection, at -810,252 enplanements (FAA forecast)

North Carolina airports that have both an observed CY2025 ACAIS enplanement and an FY2025 TAF enplanement projection are ranked below by absolute forecast variance. Absolute variance is the magnitude of ACAIS minus the TAF projection. Each variance finding is signed: a negative value means the ACAIS count is below the projection. ACAIS is calendar year CY2025. The TAF figure is federal fiscal year FY2025 (October 2024 through September 2025). Those spans are not the same, so the gap is not a same-period forecast error. The order has no ties.

1. CLT observed ACAIS is 25.87M enplanements. CLT TAF projection is 26.68M enplanements (FAA forecast). CLT signed variance is -810,252 enplanements (FAA forecast).
2. AVL observed ACAIS is 1.11M enplanements. AVL TAF projection is 1.03M enplanements (FAA forecast). AVL signed variance is 84,295 enplanements (FAA forecast).
3. ILM observed ACAIS is 912,516 enplanements. ILM TAF projection is 869,249 enplanements (FAA forecast). ILM signed variance is 43,267 enplanements (FAA forecast).
4. USA observed ACAIS is 195,791 enplanements. USA TAF projection is 175,175 enplanements (FAA forecast). USA signed variance is 20,616 enplanements (FAA forecast).
5. RDU observed ACAIS is 7.67M enplanements. RDU TAF projection is 7.65M enplanements (FAA forecast). RDU signed variance is 20,499 enplanements (FAA forecast).
6. FAY observed ACAIS is 167,660 enplanements. FAY TAF projection is 175,511 enplanements (FAA forecast). FAY signed variance is -7,851 enplanements (FAA forecast).
7. OAJ observed ACAIS is 156,204 enplanements. OAJ TAF projection is 159,295 enplanements (FAA forecast). OAJ signed variance is -3,091 enplanements (FAA forecast).
8. EWN observed ACAIS is 87,405 enplanements. EWN TAF projection is 89,552 enplanements (FAA forecast). EWN signed variance is -2,147 enplanements (FAA forecast).
9. PGV observed ACAIS is 41,290 enplanements. PGV TAF projection is 42,832 enplanements (FAA forecast). PGV signed variance is -1,542 enplanements (FAA forecast).
10. GSO observed ACAIS is 1.02M enplanements. GSO TAF projection is 1.02M enplanements (FAA forecast). GSO signed variance is 977 enplanements (FAA forecast).

**Findings and reasoning**
- *Fact*: CLT observed CY2025 ACAIS enplanements are 25.87M enplanements. CLT FY2025 TAF projection is 26.68M enplanements (FAA forecast). CLT signed variance is -810,252 enplanements (FAA forecast). [F110, F120, F191]
- *Fact*: AVL observed CY2025 ACAIS enplanements are 1.11M enplanements. AVL FY2025 TAF projection is 1.03M enplanements (FAA forecast). AVL signed variance is 84,295 enplanements (FAA forecast). [F109, F119, F192]
- *Fact*: ILM observed CY2025 ACAIS enplanements are 912,516 enplanements. ILM FY2025 TAF projection is 869,249 enplanements (FAA forecast). ILM signed variance is 43,267 enplanements (FAA forecast). [F114, F127, F193]
- *Fact*: USA observed CY2025 ACAIS enplanements are 195,791 enplanements. USA FY2025 TAF projection is 175,175 enplanements (FAA forecast). USA signed variance is 20,616 enplanements (FAA forecast). [F115, F130, F194]
- *Fact*: RDU observed CY2025 ACAIS enplanements are 7.67M enplanements. RDU FY2025 TAF projection is 7.65M enplanements (FAA forecast). RDU signed variance is 20,499 enplanements (FAA forecast). [F118, F135, F195]
- *Fact*: FAY observed CY2025 ACAIS enplanements are 167,660 enplanements. FAY FY2025 TAF projection is 175,511 enplanements (FAA forecast). FAY signed variance is -7,851 enplanements (FAA forecast). [F112, F123, F196]
- *Fact*: OAJ observed CY2025 ACAIS enplanements are 156,204 enplanements. OAJ FY2025 TAF projection is 159,295 enplanements (FAA forecast). OAJ signed variance is -3,091 enplanements (FAA forecast). [F116, F133, F197]
- *Fact*: EWN observed CY2025 ACAIS enplanements are 87,405 enplanements. EWN FY2025 TAF projection is 89,552 enplanements (FAA forecast). EWN signed variance is -2,147 enplanements (FAA forecast). [F111, F122, F198]
- *Fact*: PGV observed CY2025 ACAIS enplanements are 41,290 enplanements. PGV FY2025 TAF projection is 42,832 enplanements (FAA forecast). PGV signed variance is -1,542 enplanements (FAA forecast). [F117, F134, F199]
- *Fact*: GSO observed CY2025 ACAIS enplanements are 1.02M enplanements. GSO FY2025 TAF projection is 1.02M enplanements (FAA forecast). GSO signed variance is 977 enplanements (FAA forecast). [F113, F124, F200]
- *Inference*: Absolute-variance order, largest magnitude first, is CLT, AVL, ILM, USA, RDU, FAY, OAJ, EWN, PGV, GSO. No signed variances share a magnitude, so the rank has no ties. [F191, F192, F193, F194, F195, F196, F197, F198, F199, F200]
- *Fact*: Signed variances are negative at CLT, FAY, OAJ, EWN, and PGV, and positive at AVL, ILM, USA, RDU, and GSO. [F191, F196, F197, F198, F199, F192, F193, F194, F195, F200]

**Assumptions**
- North Carolina is the state group NC. The name is unambiguous.
- The comparable commercial set is every North Carolina airport with a CY2025 ACAIS enplanement and an FY2025 TAF enplanement. ACAIS is the FAA commercial-service boarding series, so airports absent from that series are outside this rank.
- The catalog TAF enplanement metric is fiscal-year only. FY2025 is used as the 2025 projection because that is the forecast year labelled 2025. It is not a calendar-year forecast.
- Absolute forecast variance means the magnitude of observed ACAIS enplanements minus the TAF projection, in enplanements. The stored findings keep the sign. A positive sign means ACAIS is above the projection.

**Evidence**

| id | finding | value | class | period | sources | coverage |
|---|---|---|---|---|---|---|
| F191 | difference(F110, F120) | -810,252 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F110 | FAA CY enplanements (ACAIS) — CLT — CY2025 | 25.87M enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F120 | FAA TAF enplanements — CLT — FY2025 | 26.68M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F109 | FAA CY enplanements (ACAIS) — AVL — CY2025 | 1.11M enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F119 | FAA TAF enplanements — AVL — FY2025 | 1.03M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F192 | difference(F109, F119) | 84,295 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F114 | FAA CY enplanements (ACAIS) — ILM — CY2025 | 912,516 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F127 | FAA TAF enplanements — ILM — FY2025 | 869,249 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F193 | difference(F114, F127) | 43,267 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F115 | FAA CY enplanements (ACAIS) — USA — CY2025 | 195,791 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F130 | FAA TAF enplanements — USA — FY2025 | 175,175 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F194 | difference(F115, F130) | 20,616 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F118 | FAA CY enplanements (ACAIS) — RDU — CY2025 | 7.67M enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F135 | FAA TAF enplanements — RDU — FY2025 | 7.65M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F195 | difference(F118, F135) | 20,499 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F112 | FAA CY enplanements (ACAIS) — FAY — CY2025 | 167,660 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F123 | FAA TAF enplanements — FAY — FY2025 | 175,511 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F196 | difference(F112, F123) | -7,851 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F116 | FAA CY enplanements (ACAIS) — OAJ — CY2025 | 156,204 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F133 | FAA TAF enplanements — OAJ — FY2025 | 159,295 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F197 | difference(F116, F133) | -3,091 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F111 | FAA CY enplanements (ACAIS) — EWN — CY2025 | 87,405 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F122 | FAA TAF enplanements — EWN — FY2025 | 89,552 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F198 | difference(F111, F122) | -2,147 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F117 | FAA CY enplanements (ACAIS) — PGV — CY2025 | 41,290 enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F134 | FAA TAF enplanements — PGV — FY2025 | 42,832 enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F199 | difference(F117, F134) | -1,542 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |
| F113 | FAA CY enplanements (ACAIS) — GSO — CY2025 | 1.02M enplanements | observed | CY2025 | faa_enplanements [2025] |  |
| F124 | FAA TAF enplanements — GSO — FY2025 | 1.02M enplanements (FAA forecast) | forecast | FY2025 | faa_taf [2025] |  |
| F200 | difference(F113, F124) | 977 enplanements (FAA forecast) | forecast | CY2025 | FY2025 | faa_enplanements [2025]; faa_taf [2025] |  |

**Methodology**
- `derived:difference`: difference of [FAA CY enplanements (ACAIS) — CLT — CY2025] , [FAA TAF enplanements — CLT — FY2025]
- `acais_enplanements`: FAA official calendar-year revenue passenger boardings
- `taf_enplanements`: FAA Terminal Area Forecast total enplanements (domestic + international)

**Caveats and limitations**
- FAA TAF values for forecast years are FAA's unconstrained forecast, not observations.
- Federal fiscal year (Oct–Sep).
- ACAIS CY2025 and TAF FY2025 cover different month spans. FY2025 runs from October 2024 through September 2025. The gap mixes those definitions and is not a same-period forecast error.
- Each variance finding is stored with class forecast because the TAF input is a forecast. The value is the calculated difference of an observed ACAIS count and that forecast. It is not a separate FAA forecast publication. The renderer tags it as an FAA forecast for that reason.
- North Carolina airports that have an FY2025 TAF enplanement and no CY2025 ACAIS record are omitted. Their variance cannot be established.
- This rank is not the catalog investment screen. No screening scenario, gate, flag, or contribution score was applied. It is not a valuation.
- Unmet demand, terminal capacity, fares, and profitability are not measured by ACAIS or the TAF. The data do not establish why any gap occurred.
- The built-in forecast-versus-actual operator compares T-100 passengers on a fiscal-year basis with the TAF, not ACAIS calendar-year boardings, so those results are not used.