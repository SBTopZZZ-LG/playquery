"""PlayQuery — MCP stdio server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from agents import PlayQueryAgent
from ai_providers import managed_ai_provider
from config import PlayQueryConfig, load_config
from core import PlayQueryService
from scraper import load_scraper
from search_engine import load_engine


@dataclass
class _AppContext:
    config: PlayQueryConfig
    service: PlayQueryService
    agent: PlayQueryAgent


@asynccontextmanager
async def _lifespan(_: FastMCP) -> AsyncIterator[_AppContext]:
    config = load_config()
    engine = load_engine()
    scraper = load_scraper()
    service = PlayQueryService(engine=engine, scraper=scraper)
    agent = PlayQueryAgent(service)
    yield _AppContext(config=config, service=service, agent=agent)


mcp = FastMCP("PlayQuery", lifespan=_lifespan)


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
    async with managed_ai_provider(
        app.config.ai,
        system_prompt=app.agent.system_prompt,
        tools=app.agent.tools,
    ) as provider:
        return await provider.query(query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
