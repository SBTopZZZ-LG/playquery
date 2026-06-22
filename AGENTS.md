# AGENTS.md — PlayQuery

## Dev Commands

```bash
# Setup (after cloning)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python -m patchright install chromium   # browser dep for scraper

# Run
make run              # stdio transport (default)
PLAYQUERY_MCP_TRANSPORT=streamable-http make run  # HTTP mode on :8000

# Lint / format
make lint             # ruff check .
make lint-fix         # ruff check . --fix
make format           # ruff format .

# Schema (regenerates playquery.schema.json from config.py)
make generate-schema
```

## Pre-commit Hooks

Runs on every commit: ruff fix → ruff format → basic checks (trailing whitespace, etc.) → **generate-schema hook** that fails if `playquery.schema.json` is out of date. Stage it manually with `git add playquery.schema.json`.

## What CI Runs

Only `ruff check .` and `ruff format --check .`. No type checker in CI (pyrightconfig.json exists locally but is not invoked by Makefile or pre-commit).

## Architecture

- `main.py` — FastMCP server entrypoint; single tool `ask_internet`
- `core/service.py` — `PlayQueryService` orchestrates search + scrape
- `agents/playquery.py` — `PlayQueryAgent` defines system prompt + tools exposed to AI
- `ai_providers/` — Provider abstraction + copilot / openai implementations
- `search_engine/` — SearXNG backend (factory/registry pattern)
- `scraper/` — Patchright backend (factory/registry pattern)
- `parsers/` — HTML content extraction
- `tools/` — MCP tool builders (batch_scrape, batch_search)

## Config

`playquery.yaml` is optional. `PLAYQUERY_*` env vars always win (precedence order: env var → YAML → code defaults). See `config.py` for the full env-var mapping.

## Testing

Tests are at the repo root (`test_scrape.py`, `test_search.py`). No pytest — check how they run if you need to execute them.
