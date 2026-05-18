"""Factory for loading and instantiating search engines from configuration."""

from pathlib import Path

from .base import BaseSearchEngine
from .registry import get_engine_class


def load_engine(path: str | Path = "playquery.yaml") -> BaseSearchEngine:
    """Load and instantiate the configured search engine.

    Configuration is resolved in priority order:
    ``PLAYQUERY_*`` env vars > ``playquery.yaml`` > built-in defaults.

    Args:
        path: Path to the YAML configuration file. Ignored if all required
            settings are supplied via environment variables.

    Returns:
        A fully configured search engine instance.

    Raises:
        pydantic.ValidationError: If the merged configuration is invalid.
        KeyError: If the engine type is not registered.
    """
    from config import load_config  # imported here to avoid circular init-time import

    config = load_config(path)
    engine_class = get_engine_class(config.search_engine.type)
    return engine_class(config.search_engine)
