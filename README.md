# Airport Investment Intelligence — Data Foundation (Phase 1)

A reproducible, offline-buildable aviation data foundation: original source files are archived as
immutable vintages, validated, and compiled into a single DuckDB database with full lineage.
Analytics and the conversational agent (later phases) only *read* that database.

## Quick start

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m airport_data build        # offline: committed raw archive -> data/db/airport.duckdb
.venv/bin/python -m airport_data status       # what is loaded, from which vintage, how fresh
.venv/bin/python -m airport_data coverage     # do we actually have the data the questions need?
.venv/bin/python -m pytest                    # unit + seed-integration tests (offline)
```

Refreshing from publishers (network): `python -m airport_data fetch --all-default` (plan in
[config/ingest.toml](config/ingest.toml)), or one source: `fetch --source bts_t100_segment --periods 2026-08`.
Then `build` again. Identical re-downloads are logged as `unchanged`; revised content becomes a new vintage.

## Layout

```
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

See [docs/02-phase1-data-foundation.md](docs/02-phase1-data-foundation.md) for the data model,
validation rules, coverage and known limitations.
