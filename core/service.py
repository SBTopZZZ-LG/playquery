"""Core PlayQuery service."""

import asyncio
import dataclasses
import random
from collections import defaultdict
from urllib.parse import urlparse

from logger import BaseLogger
from parsers import ParseResult, parse
from scraper.base import BaseScraper
from search_engine.base import BaseSearchEngine, SearchEngineResult

_NO_SCRAPER_ERROR = "No scraper configured in PlayQueryService."


class PlayQueryService:
    """Main PlayQuery orchestration service, coordinating search and scrape operations."""

    def __init__(
        self,
        engine: BaseSearchEngine,
        logger: BaseLogger,
        scraper: BaseScraper | None = None,
    ) -> None:
        self._engine = engine
        self._scraper = scraper
        self._logger = logger
        self._logger.debug(
            "Initialized PlayQueryService",
            engine_type=type(engine).__name__,
            scraper_type=type(scraper).__name__ if scraper is not None else None,
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        options: dict | None = None,
    ) -> list[SearchEngineResult]:
        """Perform a search query and return a list of search results."""

        # max_results is currently enforced at the service layer because the
        # engine option types do not yet expose a shared count/limit field.
        self._logger.debug(
            "Starting search request",
            query=query,
            max_results=max_results,
        )
        default_opts = self._engine.default_search_options()
        opts = dataclasses.replace(default_opts, **(options or {}))
        results = await self._engine.search(query, opts)
        trimmed_results = results[:max_results]
        self._logger.debug(
            "Completed search request",
            query=query,
            returned_count=len(trimmed_results),
            raw_count=len(results),
        )
        return trimmed_results

    async def scrape(
        self,
        url: str,
        options: dict | None = None,
    ) -> ParseResult:
        """Scrape the given URL and return the parsed main-content text."""

        if self._scraper is None:
            raise RuntimeError(_NO_SCRAPER_ERROR)
        self._logger.debug("Starting scrape request", url=url)
        default_opts = self._scraper.default_scrape_options()
        opts = dataclasses.replace(default_opts, **(options or {}))
        result = await self._scraper.scrape(url, opts)
        parsed = parse(result.html, result.final_url or url)
        self._logger.debug(
            "Completed scrape request",
            url=url,
            final_url=result.final_url or url,
            title=parsed.title,
        )
        return parsed

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
            raise RuntimeError(_NO_SCRAPER_ERROR)

        self._logger.debug(
            "Starting batch scrape",
            url_count=len(urls),
            same_host_delay=same_host_delay,
            same_host_delay_jitter=same_host_delay_jitter,
        )

        # Group URLs by hostname, preserving per-group insertion order.
        groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for i, url in enumerate(urls):
            host = urlparse(url).hostname or url
            groups[host].append((i, url))

        results: list[ParseResult | None] = [None] * len(urls)

        async def _scrape_group(indexed_urls: list[tuple[int, str]]) -> None:
            for j, (original_idx, url) in enumerate(indexed_urls):
                self._logger.debug(
                    "Scraping URL within host group", url=url, group_size=len(indexed_urls)
                )
                results[original_idx] = await self.scrape(url, options)
                if j < len(indexed_urls) - 1:
                    delay = same_host_delay + random.uniform(0, same_host_delay_jitter)
                    self._logger.debug("Sleeping between same-host scrapes", url=url, delay=delay)
                    await asyncio.sleep(delay)

        await asyncio.gather(*(_scrape_group(group) for group in groups.values()))
        parsed_results = [r for r in results if r is not None]
        self._logger.debug(
            "Completed batch scrape",
            url_count=len(urls),
            group_count=len(groups),
            result_count=len(parsed_results),
        )
        return parsed_results

    async def batch_search(
        self,
        queries: list[str],
        max_results: int = 10,
        options: dict | None = None,
    ) -> dict[str, list[SearchEngineResult]]:
        """Run multiple search queries in parallel and return results keyed by query.

        Args:
            queries: Search query strings to run.
            max_results: Maximum number of results to return per query.
            options: Search-option overrides applied to every query.

        Returns:
            A dict mapping each query string to its list of :class:`SearchEngineResult`.
        """
        self._logger.debug(
            "Starting batch search", query_count=len(queries), max_results=max_results
        )
        results = await asyncio.gather(*[self.search(q, max_results, options) for q in queries])
        payload = dict(zip(queries, results, strict=True))
        self._logger.debug("Completed batch search", query_count=len(queries))
        return payload

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
            raise RuntimeError(_NO_SCRAPER_ERROR)
        self._logger.debug("Starting search and scrape", query=query, max_results=max_results)
        search_results = await self.search(query, max_results, search_options)
        tasks = [self.scrape(r.url, scrape_options) for r in search_results]
        parsed_results = list(await asyncio.gather(*tasks))
        self._logger.debug(
            "Completed search and scrape",
            query=query,
            result_count=len(parsed_results),
        )
        return parsed_results
