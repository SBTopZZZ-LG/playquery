# PlayQuery

PlayQuery is an MCP server for web-aware research. It combines a search engine, a browser-backed scraper, and an AI provider so clients can ask questions that require current web data and receive cited answers.

The server currently exposes a single MCP tool, `ask_internet`, which searches for relevant pages, scrapes them, and synthesizes a response from the retrieved content.

## What It Uses

- `searxng` for search
- `patchright` for page loading and scraping
- An AI provider SDK, currently GitHub Copilot SDK
- FastMCP for MCP server transport support

## Requirements

- Python 3.11+
- A reachable SearXNG instance
- Browser dependencies for Patchright
- Authentication for AI providers that require it, such as GitHub Copilot

## Configuration

Configuration is loaded from `playquery.yaml` and can be overridden with `PLAYQUERY_*` environment variables.

The main sections are:

- `logging`: runtime logging level
- `ai`: provider type, model, timeout, and optional provider-specific authentication settings
- `search_engine`: search backend configuration
- `scraper`: scraper backend configuration

The bundled example config uses:

- `DEBUG` logging with a stdlib `StreamHandler`
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
export PLAYQUERY_AI_GITHUB_TOKEN=your_token_here
docker-compose up -d --build
```

The local image can include your local `playquery.yaml`. Runtime environment variables
still take precedence over the baked config, followed by `playquery.yaml`, then code defaults.

This starts:

- `playquery` on port `8000`
- `pq-searxng` on the internal Compose network

With that stack running, the MCP Streamable HTTP endpoint is available at:

```text
http://localhost:8000/mcp
```

## Install Without Cloning

For a hosted-style installation that pulls the published image from GHCR instead of building locally, use:

```bash
curl -fsSL https://raw.githubusercontent.com/SBTopZZZ-LG/playquery/main/install-with-docker-compose.sh | bash
```

On Windows PowerShell, use:

```powershell
irm https://raw.githubusercontent.com/SBTopZZZ-LG/playquery/main/install-with-docker-compose.ps1 | iex
```

The installer:

- prompts for the required environment values
- downloads `docker-compose.prod.yaml` into a local install directory
- writes a `.env` file
- starts the stack with `docker-compose`

The production-oriented Compose file is [docker-compose.prod.yaml](docker-compose.prod.yaml) and uses the published GHCR image instead of a local build.

## Environment Variables

PlayQuery reads configuration from `playquery.yaml`, then applies environment-variable overrides. The currently supported values below come from the active config models and transport setup in the codebase.

### Runtime Variables

| Variable | Purpose | Possible values | Default |
| --- | --- | --- | --- |
| `PLAYQUERY_LOGGING_LEVEL` | Logging level for the application logger. | `DEBUG` | `DEBUG` |
| `PLAYQUERY_AI_TYPE` | Selects the AI provider backend. | `copilot` | `copilot` |
| `PLAYQUERY_AI_MODEL` | Model identifier passed to the configured AI provider session. | Any non-empty AI provider supported model name, for example `claude-haiku-4.5` or `claude-sonnet-4.6` | `claude-sonnet-4.6` in code, `claude-haiku-4.5` in the bundled sample config and prod compose |
| `PLAYQUERY_AI_TIMEOUT` | AI request timeout in seconds. | Any positive number | `300.0` |
| `PLAYQUERY_AI_GITHUB_TOKEN` | GitHub token used for Copilot auth when provided. | Empty/unset, or any valid GitHub token string | unset |
| `PLAYQUERY_SEARCH_ENGINE_TYPE` | Selects the search backend. | `searxng` | `searxng` |
| `PLAYQUERY_SEARCH_ENGINE_BASE_URL` | Base URL for the SearXNG instance. | Any valid HTTP or HTTPS URL | no code default, sample config uses `http://localhost:8080`, Compose uses `http://searxng:8080` |
| `PLAYQUERY_SEARCH_ENGINE_USER_AGENT` | User-Agent header sent to the search backend. | Any string, or unset | unset in code, sample/prod compose use `PlayQuery/1.0` |
| `PLAYQUERY_SEARCH_ENGINE_TIMEOUT` | Search request timeout in seconds. | Any number | `30.0` |
| `PLAYQUERY_SCRAPER_TYPE` | Selects the scraper backend. | `patchright` | `patchright` |
| `PLAYQUERY_SCRAPER_HEADLESS` | Runs the browser headlessly. | Recommended: `true` or `false`. Truthy values accepted by the parser are `1`, `true`, `yes`, `on`; anything else is treated as false. | `true` |
| `PLAYQUERY_SCRAPER_CHANNEL` | Browser channel for Patchright. | Unset for bundled Chromium, or a browser channel string such as `chrome` or `msedge` | unset |
| `PLAYQUERY_SCRAPER_LOCALE` | Browser locale sent during scraping. | Any locale string, for example `en-US` | `en-US` |
| `PLAYQUERY_SCRAPER_TIMEOUT` | Default page-load timeout in seconds. | Any number | `30.0` |
| `PLAYQUERY_MCP_TRANSPORT` | Selects the MCP transport mode. | `stdio`, `streamable-http` | `stdio` |
| `PLAYQUERY_MCP_HOST` | Host/interface to bind for HTTP mode. | Any valid host or bind address such as `0.0.0.0` or `127.0.0.1` | `0.0.0.0` |
| `PLAYQUERY_MCP_PORT` | Port to bind for HTTP mode. | Any valid TCP port number | `8000` |
| `PLAYQUERY_MCP_PATH` | Streamable HTTP endpoint path. | Any URL path beginning with `/` | `/mcp` |
| `PLAYQUERY_MCP_JSON_RESPONSE` | Controls FastMCP JSON response behavior for HTTP transport. | Recommended: `true` or `false`. Truthy values accepted are `1`, `true`, `yes`, `on`; anything else is treated as false. | `true` |
| `PLAYQUERY_MCP_STATELESS_HTTP` | Controls FastMCP stateless HTTP behavior. | Recommended: `true` or `false`. Truthy values accepted are `1`, `true`, `yes`, `on`; anything else is treated as false. | `true` |
| `PLAYQUERY_MCP_CORS_ORIGINS` | Allowed CORS origins for HTTP mode. | `*` or a comma-separated list of origins such as `http://localhost:3000,http://localhost:6274` | `*` |

### Installer And Compose Variables

These variables are used by the installer script or the production Compose file rather than the Python app itself.

| Variable | Purpose | Possible values | Default |
| --- | --- | --- | --- |
| `PLAYQUERY_INSTALL_DIR` | Target directory created by the install script. | Any writable path | prompted interactively |
| `PLAYQUERY_RELEASE_REF` | Git ref the installer should download from. | Any existing branch, tag, or commit SHA | latest release tag if available, otherwise `main` |
| `PLAYQUERY_IMAGE_TAG` | Container tag used by [docker-compose.prod.yaml](docker-compose.prod.yaml). | Any published image tag, such as `latest`, `v1.0.0`, or a SHA tag | `latest` |
| `SEARXNG_BASE_URL` | Base URL advertised to the SearXNG container in Compose. | Any reachable URL for that container, typically `http://searxng:8080` | `http://searxng:8080` |

Example overrides:

```bash
export PLAYQUERY_SEARCH_ENGINE_BASE_URL=http://localhost:8080
export PLAYQUERY_AI_GITHUB_TOKEN=your_token_here
export PLAYQUERY_LOGGING_LEVEL=DEBUG
export PLAYQUERY_MCP_TRANSPORT=streamable-http
export PLAYQUERY_MCP_CORS_ORIGINS=http://localhost:3000
```

## Project Layout

- `main.py`: MCP server entrypoint
- `core/`: orchestration service
- `agents/`: agent definitions and tool exposure
- `ai_providers/`: provider abstraction and provider integrations
- `search_engine/`: search backends
- `scraper/`: scraping backends
- `parsers/`: HTML parsing and content extraction
- `tools/`: MCP tool builders

## Notes

- `playquery.yaml` is optional when equivalent `PLAYQUERY_*` environment variables are set.
- The Streamable HTTP mode includes CORS support for browser-based MCP tools such as MCP Inspector.
- Search and scrape behavior are implementation-driven, so additional backends can be added through the existing registry/factory pattern.
