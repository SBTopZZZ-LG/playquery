"""Scraper implementations."""

from .base import BaseScrapeOptions, BaseScraper, BaseScraperOptions, ScraperResult
from .config import ScraperConfig
from .factory import load_scraper
from .patchright import PatchrightOptions, PatchrightScrapeOptions, PatchrightScraper
from .registry import get_scraper_class, register_scraper

__all__ = [
    "BaseScrapeOptions",
    "BaseScraper",
    "BaseScraperOptions",
    "ScraperResult",
    "ScraperConfig",
    "load_scraper",
    "PatchrightOptions",
    "PatchrightScrapeOptions",
    "PatchrightScraper",
    "get_scraper_class",
    "register_scraper",
]
