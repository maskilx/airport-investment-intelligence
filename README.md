# Airport Investment Intelligence

An evidence-first analyst workspace for US airport modernization **screening and due diligence**. You ask in natural language
("Which New England airports are strong candidates for terminal expansion?", "Compare LA and Santa Ana congestion")
and get answers in which **every number is a clickable finding**: definition, period, inputs, caveats, the source dataset
and the exact file it was fetched from. Charts are built from the same findings. Follow-ups reuse earlier findings
through a structured conversation memory. Web research is optional and kept separate as cited external sources.

**Design and scoring methodology: [ARCHITECTURE.md](ARCHITECTURE.md).**

## Quick start

**This machine (data and database already present):**
```bash
./scripts/start.sh            # then open http://127.0.0.1:8765
```
The startup banner prints the mode (OFFLINE or GEMINI), the database build and the URL. It refuses to start with a
clear message if the database is missing or the model configuration is invalid. It never silently falls back.

**New machine (fresh clone):**
```bash
./scripts/bootstrap.sh        # .venv + deps, .env from .env.example, public-data download (~500 MB), DB build
./scripts/start.sh
```
The aviation data is **not in Git**. `data/raw/`, `data/db/` and `data/app/` are git-ignored.
`bootstrap.sh` re-downloads every source from its public publisher (BTS, FAA, Census, BEA, OurAirports) using the plan in
`config/ingest.toml`, checksums each file into an immutable vintage, and builds `data/db/airport.duckdb`. Curated
tables (`data/curated/`, `data/reference/`) and the fetch and validation audit log (`data/manifest/`) are small and
tracked. A fresh download gets the publishers' *current* files, so numbers can differ from this machine's vintages;
every answer shows its periods and vintages.

Tests (offline, no model calls): `.venv/bin/python -m pytest`. Seed-archive tests skip when `data/raw/` is absent.

### Offline vs Gemini mode

Mode is set in `.env`, which is copied from `.env.example` and git-ignored. Restart the app after changing it.

| Mode | `.env` | Cost |
|---|---|---|
| **Offline** (default) | `AIRPORT_MODEL=offline` | none. A rule-based planner handles the assignment questions, comparisons, trends, screens and follow-ups. **No model API calls.** |
| **Gemini** | `AIRPORT_MODEL=gemini`, `AIRPORT_ALLOW_GEMINI=1`, `GEMINI_API_KEY=…` | Free-tier Flash models only (`AIRPORT_GEMINI_MODEL`). At most `AIRPORT_GEMINI_MAX_REQUESTS` (default 25) per UTC day, counted in `data/app/gemini_usage.jsonl` across restarts. A 429 or an exhausted budget stops the turn: **no fallback**. |

The header badge shows the active mode, and in Gemini mode the requests used today. `AIRPORT_WEB=0` disables web
research, which is only offered to LLM planners.

## Data foundation

A reproducible, offline-buildable aviation data foundation. Original source files are archived as immutable vintages,
validated, and compiled into a single DuckDB database with full lineage. The analytics engine and the agent only *read* it.

```bash
.venv/bin/python -m airport_data status       # what is loaded, from which vintage, how fresh
.venv/bin/python -m airport_data coverage     # do we actually have the data the questions need?
```

## Layout

```
src/airport_analytics/  semantic layer, analysis DSL, screening, evidence (findings), grounding renderer, tools
src/airport_agent/      runtime (agent loop), memory, models (Gemini/scripted), offline planner, charts, web, provenance
src/airport_app/        FastAPI + SSE server
web/                    workspace UI (vanilla ES modules, vendored Vega-Lite)
src/airport_data/
  sources/        one adapter per source (metadata, fetch, integrity, load, checks) + registry
  rawstore.py     immutable vintaged archive: raw/<source>/<period>/<vintage>/{files, meta.json}
  ingest.py       fetch -> integrity check -> raw store; failures logged, never stored
  validation.py   generic (TableSpec-driven) + source-specific checks; error = blocking
  build.py        raw archive -> DuckDB (fallback to older valid vintage, atomic swap)
  derived.sql     conformed layer: airport identity, code decoding, semantic views, freshness
  coverage.py     declarative coverage requirements (config/coverage.toml)
  examples.py     runs docs/examples/*.sql validation cases -> docs/examples/RESULTS.md
data/
  raw/            ORIGINAL files, all vintages (committed = the seed)
  manifest/       fetch_events.jsonl + validation reports per vintage (committed)
  curated/        hand-maintained cited facts (constraints, projects)
  reference/      static code lists (US states -> Census divisions)
  db/             built database (git-ignored, always rebuildable)
```

## Extending

* **New source**: subclass `Source` (see `sources/base.py`), declare `TableSpec`s, register in
  `sources/__init__.py`, add a line to `config/ingest.toml`. Build, validation, manifest, freshness
  and lineage need no changes.
* **New airports / regions / periods**: data-driven — nothing is hard-coded per airport. Regions come
  from `ref_us_state` (Census region/division) joined through `dim_airport`.
* **New coverage requirement**: add a block to `config/coverage.toml`.
* **Downstream layers** (analytics, agent, API, observability): use `airport_data.db.connect()` and
  the conformed views; every row carries `_source_id/_period/_vintage_id`, joinable to `ingest_manifest`.

## Sources (17 registered: public bulk files, reporting-form exports, curated and reference tables)

BTS T-100 Segment (all carriers) · BTS On-Time (12 months) · BTS lookups · FAA ATADS tower operations ·
FAA CY enplanements & cargo · FAA TAF 2025 · FAA grant detail reports FY2021–25 · FAA NPIAS 2025–29 ·
FAA NASR airport records · OurAirports · Census CBSA delineation · BEA county income/population ·
curated constraints · reference lists (states, county aliases, CT geography overrides).

Docs: [ARCHITECTURE](ARCHITECTURE.md) · [01 research](docs/01-data-foundation.md) · [02 Phase 1](docs/02-phase1-data-foundation.md) (data model,
validation, identity design) · [03 Phase 1.1](docs/03-phase1.1-data-enrichment.md) (new sources, source
assessments, data dictionary additions, limitations) · [validation-case results](docs/examples/RESULTS.md) · [04 analytics plan](docs/04-phase2-analytics-plan.md) ·
[05 analytics architecture](docs/05-analytics-architecture.md) · [06 audit, review, eval](docs/06-phase2-audit-review-log.md) ·
[07 product plan](docs/07-product-phase-plan.md) · [08 memory and context](docs/08-memory-and-context.md) ·
[product-layer review](docs/reviews/grok-product-review-2026-11-04.md) · [10 consolidated assessment](docs/10-architecture-assessment.md).
