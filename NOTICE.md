# Third-party notices and data attribution

## Data

| Source | Publisher | Terms |
|---|---|---|
| T-100 Segment, Airline On-Time Performance, lookup tables | US Bureau of Transportation Statistics | US federal government work, public domain |
| Terminal Area Forecast, passenger boardings (ACAIS), ATADS, NASR, AIP grants, NPIAS | US Federal Aviation Administration | US federal government work, public domain |
| NAS Status API (live) | US Federal Aviation Administration | US federal government work, public domain |
| CAINC1 county income and population | US Bureau of Economic Analysis | US federal government work, public domain |
| CBSA delineation files | US Census Bureau | US federal government work, public domain |
| Airports and runways | OurAirports | Released to the public domain |
| Curated constraint records (`data/curated/airport_constraints.csv`) | Compiled for this project | Each row cites its source URL and quotes it verbatim; the facts belong to their publishers |

`demo/snapshot/` is an unmodified subset of the tables built from these sources (rows filtered to the demo airports;
columns the analytics never read are blanked).

## Bundled software

| Component | Version | License |
|---|---|---|
| Vega, Vega-Lite, Vega-Embed (`web/vendor/`) | 5.30.0, 5.21.0, 6.26.0 | BSD-3-Clause, see `web/vendor/LICENSE-vega.txt` |

## Python dependencies (installed by pip, not bundled)

DuckDB (MIT), FastAPI (MIT), Uvicorn (BSD-3-Clause), openpyxl (MIT), certifi (MPL-2.0); for tests, pytest (MIT) and
HTTPX (BSD-3-Clause).
