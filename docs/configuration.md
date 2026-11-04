# Configuration and operations

Developer reference: planner modes, model providers, environment variables, data operations and maintenance tools.
For an overview, start with the [README](../README.md). For design, see [ARCHITECTURE.md](../ARCHITECTURE.md).

## Planner modes

The planner is the only component that changes between modes. Tools, analytics, validation and the UI are the same
in every mode.

| `AIRPORT_MODEL` | Planner | Notes |
|---|---|---|
| `offline` (default) | Rule-based planner | No model calls and no key. It covers screens, comparisons, long-haul share, unmet-demand indicators, trends, named metrics and common follow-ups. Answers are labelled as offline |
| `gemini` | Google Gemini function calling | Needs a key and `AIRPORT_ALLOW_GEMINI=1` |
| `groq` | Groq (OpenAI-compatible API) | Needs a key and `AIRPORT_ALLOW_GROQ=1` |
| `anthropic` | Anthropic Messages API | Paid. Requires `AIRPORT_ALLOW_PAID=1` and the `anthropic` package (not installed by default); not exercised by the test suite |

```bash
./scripts/mode.sh offline | gemini | groq | status    # writes non-secret settings to .env
./scripts/start.sh --restart                          # restart after changing mode or key
```

An unknown mode is an error. No mode falls back to another one, and a provider error ends the turn with a message.

## Keys

```bash
./scripts/configure-gemini-key.sh            # hidden input; verifies the key against the model catalog
./scripts/configure-groq-key.sh              # separate key, separate Keychain item
./scripts/configure-gemini-key.sh --remove   # delete the key and return to offline mode
```

* On macOS, keys are stored in the Keychain (service `airport-investment-intelligence`).
* Elsewhere they go to `.env` with mode `600`.
* `.env` is git-ignored, and keys are never written to logs.
* Variables set in the shell take precedence over `.env`.

## Provider limits and budgets

| Variable | Default | Purpose |
|---|---|---|
| `AIRPORT_GEMINI_MODEL` | a Flash model | Only free-tier Flash ids are accepted unless `AIRPORT_ALLOW_PAID=1` |
| `AIRPORT_GEMINI_MAX_REQUESTS` | `25` | Requests per UTC day, persisted in `data/app/gemini_usage.jsonl` |
| `AIRPORT_GROQ_MODEL` | `openai/gpt-oss-120b` | Tool-capable model id |
| `AIRPORT_GROQ_MAX_REQUESTS` | `60` | Requests per UTC day |
| `AIRPORT_GROQ_MAX_CONTEXT_TOKENS` | `8000` | Hard cap per request |
| `AIRPORT_ALLOW_PAID` | unset | Must be `1` for any paid model |

**Groq context cap.** The system prompt and tool schemas take about 6k tokens. The 8k default therefore leaves
little room for a real question. Use `AIRPORT_GROQ_MAX_CONTEXT_TOKENS=60000` on a plan whose rate limits allow it.

**Live checks.** Each check sends one real question and is capped at 5 requests, counted persistently:

```bash
.venv/bin/python tools/gemini_smoke.py
.venv/bin/python tools/groq_smoke.py
```

## Other settings

| Variable | Purpose |
|---|---|
| `AIRPORT_DATA_DIR` | Data root, instead of `./data`. It holds `raw/`, `db/` and `app/`. `scripts/demo.sh` sets it to `demo/data` |
| `AIRPORT_WEB=0` | Disables web research (offered only to LLM planners) |

## Data operations

```bash
.venv/bin/python -m airport_data fetch --all-default   # download public sources (plan: config/ingest.toml)
.venv/bin/python -m airport_data build                 # raw archive -> DuckDB; validation blocks bad files
.venv/bin/python -m airport_data status                # loaded periods, versions, freshness
.venv/bin/python -m airport_data coverage              # declarative coverage requirements (config/coverage.toml)
.venv/bin/python -m airport_data demo-import           # demo/snapshot -> demo/data/db (used by scripts/demo.sh)
```

**Raw archive.** Downloads are stored as immutable, checksummed versions under `data/raw/<source>/<period>/<version>/`.
A rebuild from the same archive is bit-for-bit identical. A source that fails validation keeps serving its last
valid version.

**Curated records** (`data/curated/airport_constraints.csv`) are loaded through the same pipeline. Each row needs a
source URL, a verbatim quote and an evidence level (`verified:primary`, `verified:secondary`,
`verified:search_snippet` or `unverified:*`). After editing the file, load and rebuild:

```bash
.venv/bin/python -m airport_data fetch --source curated_constraints
.venv/bin/python -m airport_data build
```

**Demo snapshot.** `demo/snapshot/` is generated from a full local database. It keeps every reference and annual
table, plus the flight rows that touch New England airports, LAX, SNA, SFO and ANC. Regenerate it only when the full
data changes:

```bash
.venv/bin/python tools/build_demo_snapshot.py
```

## Maintenance tools

| Tool | Purpose |
|---|---|
| `tools/link_audit.py` | Checks every external link the product shows and prints a JSON report. Dead links go in `config/link_status.toml` |
| `tools/roq.py` | Read-only SQL over the built database |
| `python -m airport_analytics call <tool> '<json>'` | Calls any agent tool from the terminal (used by `eval/run_eval.py`) |
| `tools/render_architecture.py` | Regenerates `docs/images/architecture.svg` |
| `eval/questions.jsonl`, `eval/run_eval.py` | 70 graded questions, run through an external CLI agent restricted to the tool CLI |
