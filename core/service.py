"""Core PlayQuery service."""

import asyncio
import dataclasses
import random
from collections import defaultdict
from urllib.parse import urlparse

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

    async def batch_scrape(
        self,
        urls: list[str],
        options: dict | None = None,
        same_host_delay: float = 1.0,
        same_host_delay_jitter: float = 1.0,
    ) -> list[ParseResult]:
        """Scrape multiple URLs with per-hostname rate limiting.

        URLs sharing a hostname are scraped sequentially with a delay of
        ``same_host_delay + uniform(0, same_host_delay_jitter)`` seconds between
        each request.  URLs belonging to different hostnames are scraped in
        parallel.  Results are returned in the same order as *urls*.

        Args:
            urls: URLs to scrape.
            options: Scrape-option overrides forwarded to each :meth:`scrape` call.
            same_host_delay: Minimum seconds to wait between requests to the same host.
            same_host_delay_jitter: Upper bound of the extra random delay added on top
                of *same_host_delay*.  A non-zero value makes the inter-request timing
                less predictable, reducing the chance of triggering rate limits or bot
                detection.
        """
        if self._scraper is None:
            raise RuntimeError("No scraper configured in PlayQueryService.")

        # Group URLs by hostname, preserving per-group insertion order.
        groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for i, url in enumerate(urls):
            host = urlparse(url).hostname or url
            groups[host].append((i, url))

        results: list[ParseResult | None] = [None] * len(urls)

        async def _scrape_group(indexed_urls: list[tuple[int, str]]) -> None:
            for j, (original_idx, url) in enumerate(indexed_urls):
                results[original_idx] = await self.scrape(url, options)
                if j < len(indexed_urls) - 1:
                    delay = same_host_delay + random.uniform(0, same_host_delay_jitter)
                    await asyncio.sleep(delay)

        await asyncio.gather(*(_scrape_group(group) for group in groups.values()))
        return [r for r in results if r is not None]

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
