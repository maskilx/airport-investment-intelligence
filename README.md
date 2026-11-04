# Airport Investment Intelligence

An evidence-first analyst workspace for US airport modernization **screening and due diligence**. You ask in natural language
("Which New England airports are strong candidates for terminal expansion?", "Compare LA and Santa Ana congestion")
and get answers in which **every number is a clickable finding**: definition, period, inputs, caveats, the source dataset
and the exact file it was fetched from. Charts are built from the same findings. Follow-ups reuse earlier findings
through a structured conversation memory. Web research is optional and kept separate as cited external sources.

**Design and scoring methodology: [ARCHITECTURE.md](ARCHITECTURE.md).**

## Quick start

Permanent location on this Mac: **`~/Downloads/airport-investment-intelligence`**. Data and database are local here.

```bash
~/Downloads/airport-investment-intelligence/scripts/start.sh             # open http://127.0.0.1:8765
~/Downloads/airport-investment-intelligence/scripts/start.sh --restart   # after changing mode or key
~/Downloads/airport-investment-intelligence/scripts/start.sh --stop
```
The script works from any directory. The banner prints the mode (OFFLINE or GEMINI), the database build and the URL.
If the app is already running, it prints where instead of starting a second copy. It refuses to start, with a clear
reason, if the database is missing or the Gemini configuration is invalid. It never silently falls back to offline.

**New machine (fresh clone):** `./scripts/bootstrap.sh` creates `.venv`, installs dependencies, creates `.env` from
`.env.example`, downloads the public data (~500 MB) and builds the database. Then run `./scripts/start.sh`.
The aviation data is **not in Git**. `data/raw/`, `data/db/` and `data/app/` are git-ignored and recreated from the
public publishers using `config/ingest.toml`. A fresh download gets the publishers' current files, so numbers can
differ; every answer shows its periods and vintages.

Tests (offline, no model calls): `.venv/bin/python -m pytest`. Seed-archive tests skip when `data/raw/` is absent.

### Offline and Gemini mode

```bash
./scripts/configure-gemini-key.sh    # set or replace the key: hidden input, stored in the macOS Keychain
./scripts/mode.sh gemini             # or: ./scripts/mode.sh offline   |   ./scripts/mode.sh status
./scripts/start.sh --restart
```
* **Offline** (default): a rule-based planner. **No model API calls.**
* **Gemini**: the key is read with hidden input and checked against Google's model catalog (a metadata call, not a
  generation request). It is stored in the **macOS Keychain** (service `airport-investment-intelligence`) and never in
  a file, a command line or a log. If the Keychain is unavailable it goes in `.env` with `chmod 600`; `.env` is
  git-ignored. The helper selects a verified free-tier Flash model.
  * Requests are capped by `AIRPORT_GEMINI_MAX_REQUESTS` (default 25 per UTC day), counted in `data/app/gemini_usage.jsonl` across restarts.
  * A 429 or an exhausted budget stops the turn: **no fallback**. Paid models need `AIRPORT_ALLOW_PAID=1` (do not set it).
* `./scripts/configure-gemini-key.sh --remove` deletes the key and returns to offline.

The header badge shows the active mode, and in Gemini mode the requests used today.

**Groq** (`openai/gpt-oss-120b`, see [docs/model-provider-review.md](docs/model-provider-review.md)):
```bash
./scripts/configure-groq-key.sh      # hidden input; own Keychain item (the Gemini key is untouched)
./scripts/mode.sh groq && ./scripts/start.sh --restart
```
* Free tier: 8k tokens per minute. The app paces requests and caps context per request, so expect minutes per question.
* On the Developer plan, set `AIRPORT_GROQ_MAX_CONTEXT_TOKENS=60000`.
* There is no fallback to other providers.
* Live check: `.venv/bin/python tools/groq_smoke.py`, limited to 5 requests in total.

### Live voice
Click the microphone to start a voice conversation. It uses the same conversation, agent, evidence and validation as text chat.
* **States:** listening, processing, speaking.
* **Interrupt:** talk over the answer, or press Esc.
* **Typing** always works.
* **Speech-to-text:**
  * Default: the browser's speech recognition (Chrome or Safari; no key).
  * With Groq: set `AIRPORT_VOICE_STT=groq` in `.env` to use Groq Whisper on the server (needs the Groq key). It has its own daily cap, `AIRPORT_VOICE_MAX_REQUESTS`.
* **Language:** English. Headphones avoid echo. Design and research: [docs/voice-architecture-review.md](docs/voice-architecture-review.md).

### Demo in five steps
1. Run `./scripts/start.sh` and open http://127.0.0.1:8765. Choose the provider first with `./scripts/mode.sh offline|gemini|groq`.
2. Ask a factual question: "What is the percentage of long haul flights out of Anchorage airport?", then follow up with "Use 2000 miles instead".
3. Ask for a comparison: "Compare LA and Santa Ana airport congestion levels."
4. Ask for a decision: "Which airports in New England are strong candidates for terminal expansion?", then "Which one should we prioritize?"
5. Inspect the evidence: click any highlighted value to see its definition, inputs, the dataset page and the exact raw file or download form. To try voice, press the microphone and ask "What is the unmet flight demand at SFO and why?"

**One-question live check:** `.venv/bin/python tools/gemini_smoke.py` runs one LAX vs SNA congestion question. It
allows at most 5 model requests, tracked in a persistent smoke-test counter that is separate from the daily budget.

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
