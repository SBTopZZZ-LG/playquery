"""PlayQuery MCP server."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter

from mcp.server.fastmcp import Context, FastMCP
from starlette.middleware.cors import CORSMiddleware

from agents import PlayQueryAgent
from ai_providers import managed_ai_provider
from config import PlayQueryConfig, load_config
from core import PlayQueryService
from logger import BaseLogger, configure_logger
from scraper import load_scraper
from search_engine import load_engine


@dataclass
class _AppContext:
    config: PlayQueryConfig
    logger: BaseLogger
    service: PlayQueryService
    agent: PlayQueryAgent


@asynccontextmanager
async def _lifespan(_: FastMCP) -> AsyncIterator[_AppContext]:
    config = load_config()
    logger = configure_logger(config.logging)
    logger.debug("Loaded PlayQuery configuration")
    engine = load_engine(config=config, logger=logger.child("search_engine"))
    scraper = load_scraper(config=config, logger=logger.child("scraper"))
    service = PlayQueryService(
        engine=engine,
        scraper=scraper,
        logger=logger.child("core.service"),
    )
    agent = PlayQueryAgent(service, logger.child("agents.playquery"))
    logger.debug("Application lifespan initialized")
    yield _AppContext(config=config, logger=logger, service=service, agent=agent)


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_MCP_HOST = os.environ.get("PLAYQUERY_MCP_HOST", "0.0.0.0")
_MCP_PORT = int(os.environ.get("PLAYQUERY_MCP_PORT", "8000"))
_MCP_PATH = os.environ.get("PLAYQUERY_MCP_PATH", "/mcp")
_MCP_JSON_RESPONSE = _parse_bool_env("PLAYQUERY_MCP_JSON_RESPONSE", True)
_MCP_STATELESS_HTTP = _parse_bool_env("PLAYQUERY_MCP_STATELESS_HTTP", True)


def _cors_origins() -> list[str]:
    raw = os.environ.get("PLAYQUERY_MCP_CORS_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


mcp = FastMCP(
    "PlayQuery",
    lifespan=_lifespan,
    host=_MCP_HOST,
    port=_MCP_PORT,
    streamable_http_path=_MCP_PATH,
    json_response=_MCP_JSON_RESPONSE,
    stateless_http=_MCP_STATELESS_HTTP,
)


def _run_server() -> None:
    transport = os.environ.get("PLAYQUERY_MCP_TRANSPORT", "stdio").strip().lower()

    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport == "streamable-http":
        import uvicorn

        app = CORSMiddleware(
            app=mcp.streamable_http_app(),
            allow_origins=_cors_origins(),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
        uvicorn.run(app, host=_MCP_HOST, port=_MCP_PORT, log_level="info")
        return

    raise ValueError(
        "Unsupported PLAYQUERY_MCP_TRANSPORT value. Expected 'stdio' or 'streamable-http'."
    )


@mcp.tool()
async def ask_internet(query: str, ctx: Context) -> str:  # type: ignore[type-arg]
    """Research a question on the internet and return a thorough, cited answer.

    Searches the web, reads the most relevant pages, and synthesises a response
    with inline numbered citations and a References section.  Use this whenever
    you need current, specific, or source-backed information.

    Args:
        query: The question or research topic to investigate.
    """
    app: _AppContext = ctx.request_context.lifespan_context
    app.logger.debug("Received ask_internet request", query=query)
    try:
        async with managed_ai_provider(
            app.config.ai,
            logger=app.logger.child("ai_providers"),
            system_prompt=app.agent.system_prompt,
            tools=app.agent.tools,
        ) as provider:
            started_at = perf_counter()
            response = await provider.query(query)
            duration_seconds = perf_counter() - started_at
            app.logger.debug(
                "Completed ask_internet request",
                query=query,
                duration_seconds=round(duration_seconds, 3),
            )
            return f"{response}\n\nResponse time: {duration_seconds:.1f}s"
    except Exception as exc:
        app.logger.error(
            "ask_internet request failed",
            exc_info=exc,
            query=query,
        )
        raise


if __name__ == "__main__":
    _run_server()
