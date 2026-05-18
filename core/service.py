"""Core PlayQuery service."""

import asyncio
import dataclasses

from parsers import ParseResult, parse
from scraper.base import BaseScraper
from search_engine.base import BaseSearchEngine, SearchEngineResult


class PlayQueryService:
    """Main PlayQuery orchestration service, coordinating search and scrape operations"""

    def __init__(
        self,
        engine: BaseSearchEngine,
        scraper: BaseScraper | None = None,
    ) -> None:
        self._engine = engine
        self._scraper = scraper

    async def search(
        self,
        query: str,
        max_results: int = 10,
        options: dict | None = None,
    ) -> list[SearchEngineResult]:
        """Perform a search query and return a list of search results."""

        # TODO (post-MVP): pass max_results into engine-level options once
        # SearXNG (and future engines) expose a count/limit parameter.
        default_opts = self._engine.default_search_options()
        opts = dataclasses.replace(default_opts, **(options or {}))
        results = await self._engine.search(query, opts)
        return results[:max_results]

    async def scrape(
        self,
        url: str,
        options: dict | None = None,
    ) -> ParseResult:
        """Scrape the given URL and return the parsed main-content text."""

        if self._scraper is None:
            raise RuntimeError("No scraper configured in PlayQueryService.")
        default_opts = self._scraper.default_scrape_options()
        opts = dataclasses.replace(default_opts, **(options or {}))
        result = await self._scraper.scrape(url, opts)
        return parse(result.html, result.final_url or url)

    async def search_and_scrape(
        self,
        query: str,
        max_results: int = 10,
        search_options: dict | None = None,
        scrape_options: dict | None = None,
    ) -> list[ParseResult]:
        """
        Perform a search query, scrape the resulting URLs, and return a list of parsed results.
        """

        if self._scraper is None:
            raise RuntimeError("No scraper configured in PlayQueryService.")
        search_results = await self.search(query, max_results, search_options)
        tasks = [self.scrape(r.url, scrape_options) for r in search_results]
        return list(await asyncio.gather(*tasks))
