"""Factory for loading and instantiating scrapers from configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from logger import BaseLogger

from .base import BaseScraper
from .registry import get_scraper_class

if TYPE_CHECKING:
    from config import PlayQueryConfig


def load_scraper(
    path: str | Path = "playquery.yaml",
    *,
    config: PlayQueryConfig | None = None,
    logger: BaseLogger,
) -> BaseScraper:
    """Load and instantiate the configured scraper.

    Configuration is resolved in priority order:
    ``PLAYQUERY_*`` env vars > ``playquery.yaml`` > built-in defaults.

    Args:
        path: Path to the YAML configuration file. Ignored if all required
            settings are supplied via environment variables.
        config: Pre-loaded application config. When provided, *path* is ignored.
        logger: Logger to bind to the created scraper instance.

    Returns:
        A fully configured scraper instance.

    Raises:
        pydantic.ValidationError: If the merged configuration is invalid.
        KeyError: If the scraper type is not registered.
        ValueError: If no scraper type is configured.
    """
    if config is None:
        from config import load_config

        active_config = load_config(path)
    else:
        active_config = config

    if active_config.scraper is None:
        raise ValueError(
            "No scraper configured. Set PLAYQUERY_SCRAPER_TYPE or add a 'scraper:' "
            "section to playquery.yaml."
        )

    scraper_class = get_scraper_class(active_config.scraper.type)
    logger.debug(
        "Loading scraper",
        scraper_type=active_config.scraper.type,
        scraper_class=scraper_class.__name__,
    )
    return scraper_class(active_config.scraper, logger)
