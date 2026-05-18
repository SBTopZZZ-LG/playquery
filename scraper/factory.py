"""Factory for loading and instantiating scrapers from configuration."""

from pathlib import Path

from .base import BaseScraper
from .registry import get_scraper_class


def load_scraper(path: str | Path = "playquery.yaml") -> BaseScraper:
    """Load and instantiate the configured scraper.

    Configuration is resolved in priority order:
    ``PLAYQUERY_*`` env vars > ``playquery.yaml`` > built-in defaults.

    Args:
        path: Path to the YAML configuration file. Ignored if all required
            settings are supplied via environment variables.

    Returns:
        A fully configured scraper instance.

    Raises:
        pydantic.ValidationError: If the merged configuration is invalid.
        KeyError: If the scraper type is not registered.
        ValueError: If no scraper type is configured.
    """
    from config import load_config  # imported here to avoid circular init-time import

    config = load_config(path)

    if config.scraper is None:
        raise ValueError(
            "No scraper configured. Set PLAYQUERY_SCRAPER_TYPE or add a 'scraper:' "
            "section to playquery.yaml."
        )

    scraper_class = get_scraper_class(config.scraper.type)
    return scraper_class(config.scraper)
