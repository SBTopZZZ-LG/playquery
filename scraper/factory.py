"""Factory for loading and instantiating scrapers from playquery.yaml."""

from pathlib import Path

import yaml

from .base import BaseScraper
from .registry import get_scraper_class


def load_scraper(path: str | Path = "playquery.yaml") -> BaseScraper:
    """Load and instantiate the configured scraper from a YAML file.

    Args:
        path: Path to the YAML configuration file. Defaults to playquery.yaml.

    Returns:
        A fully configured scraper instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValidationError: If the config file fails Pydantic validation.
        KeyError: If the scraper type is not registered.
        ValueError: If no scraper is configured in the YAML file.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    from config import PlayQueryConfig  # imported here to avoid circular init-time import

    config = PlayQueryConfig.model_validate(data)

    if config.scraper is None:
        raise ValueError(
            "No scraper configured in playquery.yaml. Add a 'scraper:' section to enable scraping."
        )

    scraper_class = get_scraper_class(config.scraper.type)
    return scraper_class(config.scraper)
