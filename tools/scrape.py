"""Scrape tool builder."""

import dataclasses

from pydantic import Field

from ai_providers import BaseTool, define_tool
from core.service import PlayQueryService
from parsers import ParseResult

from ._utils import make_params_model


def make_scrape_tool(service: PlayQueryService) -> BaseTool:
    """Return a scrape tool bound to *service*.

    The tool's parameter schema is derived dynamically from the scraper's
    concrete scrape-options dataclass, so the agent always sees the exact
    set of options the configured scraper supports.

    Raises:
        ValueError: If *service* has no scraper configured.
    """
    if service._scraper is None:
        raise ValueError("Cannot build a scrape tool: no scraper configured in PlayQueryService.")

    options_type = type(service._scraper.default_scrape_options())

    primary = {
        "url": (str, Field(description="The URL to scrape.")),
    }
    ScrapeParams = make_params_model("ScrapeParams", primary, options_type)

    async def _handler(params) -> ParseResult:  # type: ignore[no-untyped-def]
        scrape_options = {f.name: getattr(params, f.name) for f in dataclasses.fields(options_type)}
        return await service.scrape(params.url, scrape_options)

    _handler.__annotations__ = {"params": ScrapeParams, "return": ParseResult}

    return define_tool(description="Scrape a URL and return the parsed main-content text.")(
        _handler
    )
