"""Batch-scrape tool builder."""

import dataclasses

from pydantic import Field

from ai_providers import BaseTool, define_tool
from core.service import PlayQueryService
from logger import BaseLogger
from parsers import ParseResult

from ._utils import make_params_model, sanitize_schema


def make_batch_scrape_tool(service: PlayQueryService, logger: BaseLogger) -> BaseTool:
    """Return a batch-scrape tool bound to *service*.

    Accepts a list of URLs and delegates to :meth:`PlayQueryService.batch_scrape`,
    which handles per-hostname rate limiting automatically: URLs from different
    hosts are fetched in parallel while URLs sharing a host are fetched
    sequentially with a delay to avoid triggering rate limits or bot detection.

    Raises:
        ValueError: If *service* has no scraper configured.
    """
    if service._scraper is None:  # pylint: disable=protected-access
        raise ValueError(
            "Cannot build a batch-scrape tool: no scraper configured in PlayQueryService."
        )

    options_type = type(service._scraper.default_scrape_options())  # pylint: disable=protected-access

    primary = {
        "urls": (
            list[str],
            Field(description="List of URLs to scrape."),
        ),
    }
    batch_scrape_params = make_params_model("BatchScrapeParams", primary, options_type)

    async def _handler(params) -> list[ParseResult]:  # type: ignore[no-untyped-def]
        scrape_options = {f.name: getattr(params, f.name) for f in dataclasses.fields(options_type)}
        logger.debug("Invoking batch_scrape tool", url_count=len(params.urls))
        return await service.batch_scrape(params.urls, scrape_options)

    _handler.__annotations__ = {"params": batch_scrape_params, "return": list[ParseResult]}

    tool = define_tool(
        name="batch_scrape",
        description=(
            "Scrape multiple URLs and return parsed main-content text for each. "
            "URLs from different hostnames are fetched in parallel; multiple URLs "
            "from the same hostname are fetched sequentially to respect rate limits. "
            "Use this when you already know which specific pages you want to read — "
            "for example, after a search revealed the relevant links, or when the user "
            "provided URLs directly.  Always pass all chosen URLs in a single call; "
            "never call this tool repeatedly for individual URLs."
        ),
    )(_handler)
    tool.parameters = sanitize_schema(tool.parameters)
    return tool
