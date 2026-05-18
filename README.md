# PlayQuery

PlayQuery is an MCP server for web-aware research. It combines a search engine, a browser-backed scraper, and an AI provider so clients can ask questions that require current web data and receive cited answers.

The server currently exposes a single MCP tool, `ask_internet`, which searches for relevant pages, scrapes them, and synthesizes a response from the retrieved content.

## What It Uses

- `searxng` for search
- `patchright` for page loading and scraping
- GitHub Copilot SDK for the AI session
- FastMCP for MCP server transport support

## Requirements

- Python 3.11+
- A reachable SearXNG instance
- Browser dependencies for Patchright
- GitHub authentication for the Copilot provider when required

## Configuration

Configuration is loaded from `playquery.yaml` and can be overridden with `PLAYQUERY_*` environment variables.

The main sections are:

- `ai`: provider type, model, timeout, and optional GitHub token
- `search_engine`: search backend configuration
- `scraper`: scraper backend configuration

The bundled example config uses:

- `copilot` as the AI provider
- `searxng` as the search engine
- `patchright` as the scraper

## Local Development

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m patchright install chromium
```

Useful commands:

```bash
make run
make lint
make lint-fix
make format
make generate-schema
```

By default, the server runs over stdio:

```bash
python main.py
```

## HTTP Mode

PlayQuery also supports Streamable HTTP for browser-based tools and containerized deployments.

Example:

```bash
PLAYQUERY_MCP_TRANSPORT=streamable-http \
PLAYQUERY_MCP_HOST=0.0.0.0 \
PLAYQUERY_MCP_PORT=8000 \
python main.py
```

The default HTTP endpoint is:

```text
http://localhost:8000/mcp
```

## Docker Compose

The repository includes a simple Compose stack for PlayQuery and SearXNG:

```bash
docker-compose up -d --build
```

This starts:

- `playquery` on port `8000`
- `pq-searxng` on the internal Compose network

With that stack running, the MCP Streamable HTTP endpoint is available at:

```text
http://localhost:8000/mcp
```

## Example Environment Overrides

```bash
export PLAYQUERY_SEARCH_ENGINE_BASE_URL=http://localhost:8080
export PLAYQUERY_AI_GITHUB_TOKEN=your_token_here
export PLAYQUERY_MCP_TRANSPORT=streamable-http
```

## Project Layout

- `main.py`: MCP server entrypoint
- `core/`: orchestration service
- `agents/`: agent definitions and tool exposure
- `ai_providers/`: provider abstraction and Copilot integration
- `search_engine/`: search backends
- `scraper/`: scraping backends
- `parsers/`: HTML parsing and content extraction
- `tools/`: MCP tool builders

## Notes

- `playquery.yaml` is optional when equivalent `PLAYQUERY_*` environment variables are set.
- The Streamable HTTP mode includes CORS support for browser-based MCP tools such as MCP Inspector.
- Search and scrape behavior are implementation-driven, so additional backends can be added through the existing registry/factory pattern.
