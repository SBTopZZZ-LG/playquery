"""Factory for loading and instantiating search engines from playquery.yaml."""

from pathlib import Path

import yaml

from .base import BaseSearchEngine
from .registry import get_engine_class


def load_engine(path: str | Path = "playquery.yaml") -> BaseSearchEngine:
    """Load and instantiate the configured search engine from a YAML file.

    Args:
        path: Path to the YAML configuration file. Defaults to playquery.yaml.

    Returns:
        A fully configured search engine instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValidationError: If the config file fails Pydantic validation.
        KeyError: If the engine type is not registered.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    from config import PlayQueryConfig  # imported here to avoid circular init-time import

    config = PlayQueryConfig.model_validate(data)
    engine_class = get_engine_class(config.search_engine.type)
    return engine_class(config.search_engine)
