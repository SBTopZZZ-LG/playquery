"""Scraper base classes and interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel


class BaseScraperOptions(BaseModel):
    """Base Pydantic model for scraper configuration options."""


@dataclass
class BaseScrapeOptions:
    """Base class for per-request options used in individual scrape calls."""


@dataclass
class ScraperResult:
    """Represents the raw output of a single scrape operation."""

    url: str
    """The original URL that was requested."""

    html: str
    """Full page HTML as returned by the scraper. Parsing is left to the caller."""

    final_url: str | None = None
    """The URL after any redirects, if it differs from the requested URL."""


T = TypeVar("T", bound=BaseScraperOptions)
R = TypeVar("R", bound=BaseScrapeOptions)


class BaseScraper(ABC, Generic[T, R]):
    """Abstract base class for scraper implementations."""

    options: T

    def __init__(self, options: T):
        """Initialize the base scraper.

        Args:
            options: Scraper-specific configuration object.
        """

        self.options = options

    @abstractmethod
    def default_scrape_options(self) -> R:
        """Return a default per-scrape options instance for this scraper."""

    @abstractmethod
    async def scrape(self, url: str, options: R) -> ScraperResult:
        """Scrape the given URL and return the raw page DOM.

        Args:
            url: The URL to scrape.
            options: Per-request scrape options.

        Returns:
            A ScraperResult containing the full page HTML and metadata.
        """
