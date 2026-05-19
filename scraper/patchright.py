"""Patchright scraper implementation."""

from dataclasses import dataclass, field
from typing import Literal

from patchright.async_api import async_playwright

from .base import BaseScrapeOptions, BaseScraper, BaseScraperOptions, ScraperResult
from .registry import register_scraper

SCRAPER_TYPE = "patchright"


class PatchrightOptions(BaseScraperOptions):
    """Pydantic model for Patchright scraper configuration."""

    type: Literal[SCRAPER_TYPE] = SCRAPER_TYPE  # type: ignore[valid-type]

    headless: bool = True
    """Run the browser in headless mode. Defaults to True."""

    channel: str | None = None
    """Browser channel to use (e.g. 'chrome', 'msedge'). Defaults to bundled Chromium."""

    locale: str | None = "en-US"
    """Browser locale sent with every request. Defaults to 'en-US'."""

    timeout: float = 30.0
    """Default page-load timeout in seconds. Can be overridden per request."""


@dataclass
class PatchrightScrapeOptions(BaseScrapeOptions):
    """Per-request options for Patchright scrape calls."""

    wait_until: Literal["load", "domcontentloaded", "networkidle", "commit"] = "domcontentloaded"
    """
    Navigation event to wait for before capturing the DOM.
    One of: 'load', 'domcontentloaded', 'networkidle', 'commit'.
    """

    extra_headers: dict[str, str] = field(default_factory=dict)
    """Additional HTTP headers to send with the request."""

    timeout: float | None = None
    """Per-request page-load timeout in seconds. Overrides the engine-level default when set."""


@register_scraper(SCRAPER_TYPE)
class PatchrightScraper(BaseScraper[PatchrightOptions, PatchrightScrapeOptions]):
    """Scraper implementation backed by Patchright (stealth Playwright)."""

    def default_scrape_options(self) -> PatchrightScrapeOptions:
        return PatchrightScrapeOptions()

    async def scrape(self, url: str, options: PatchrightScrapeOptions) -> ScraperResult:
        """Navigate to *url* and return the full page HTML.

        A fresh browser instance is launched and torn down for every call,
        keeping the implementation stateless.

        Args:
            url: The URL to scrape.
            options: Per-request options (wait_until, extra_headers, timeout).

        Returns:
            A ScraperResult with the raw HTML and the post-redirect final URL.
        """
        timeout_ms = (options.timeout or self.options.timeout) * 1000
        self.logger.debug(
            "Starting Patchright scrape",
            url=url,
            wait_until=options.wait_until,
            timeout_ms=timeout_ms,
        )

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.options.headless,
                channel=self.options.channel,
            )
            context = await browser.new_context(locale=self.options.locale)

            try:
                page = await context.new_page()

                if options.extra_headers:
                    await page.set_extra_http_headers(options.extra_headers)

                await page.goto(
                    url,
                    wait_until=options.wait_until,
                    timeout=timeout_ms,
                )

                html = await page.content()
                final_url = page.url
            finally:
                await context.close()
                await browser.close()

        self.logger.debug(
            "Completed Patchright scrape",
            url=url,
            final_url=final_url,
            html_size=len(html),
        )

        return ScraperResult(
            url=url,
            html=html,
            final_url=final_url if final_url != url else None,
        )
