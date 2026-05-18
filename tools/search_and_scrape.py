"""Search-and-scrape tool builder."""

import dataclasses

from pydantic import Field

from ai_providers import BaseTool, define_tool
from core.service import PlayQueryService
from parsers import ParseResult

from ._utils import make_params_model


def make_search_and_scrape_tool(service: PlayQueryService) -> BaseTool:
    """Return a combined search-and-scrape tool bound to *service*.

    The tool searches the web for *query*, scrapes the top *max_results* pages
    in parallel, and returns the parsed content for each.  The parameter schema
    is derived dynamically from the engine's search-options dataclass so the
    agent always sees the exact options the configured engine supports.

    Raises:
        ValueError: If *service* has no scraper configured.
    """
    if service._scraper is None:
        raise ValueError(
            "Cannot build a search-and-scrape tool: no scraper configured in PlayQueryService."
        )

    options_type = type(service._engine.default_search_options())

    primary = {
        "query": (str, Field(description="The search query string.")),
        "max_results": (
            int,
            Field(
                default=5,
                description=(
                    "Number of search results to scrape. "
                    "Prefer the default (5) unless the topic requires broader coverage."
                ),
            ),
        ),
    }
    SearchAndScrapeParams = make_params_model("SearchAndScrapeParams", primary, options_type)

    async def _handler(params) -> list[ParseResult]:  # type: ignore[no-untyped-def]
        engine_options = {f.name: getattr(params, f.name) for f in dataclasses.fields(options_type)}
        return await service.search_and_scrape(params.query, params.max_results, engine_options)

    _handler.__annotations__ = {"params": SearchAndScrapeParams, "return": list[ParseResult]}

    return define_tool(
        description=(
            "Search the web for a query and scrape the top results in one call. "
            "Returns parsed main-content text for each page. "
            "Prefer this for broad research queries where you want depth without "
            "manually selecting which links to visit."
        )
    )(_handler)
