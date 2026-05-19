"""Factory for loading and instantiating search engines from configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from logger import BaseLogger

from .base import BaseSearchEngine
from .registry import get_engine_class

if TYPE_CHECKING:
    from config import PlayQueryConfig


def load_engine(
    path: str | Path = "playquery.yaml",
    *,
    config: PlayQueryConfig | None = None,
    logger: BaseLogger,
) -> BaseSearchEngine:
    """Load and instantiate the configured search engine.

    Configuration is resolved in priority order:
    ``PLAYQUERY_*`` env vars > ``playquery.yaml`` > built-in defaults.

    Args:
        path: Path to the YAML configuration file. Ignored if all required
            settings are supplied via environment variables.
        config: Pre-loaded application config. When provided, *path* is ignored.
        logger: Logger to bind to the created search engine instance.

    Returns:
        A fully configured search engine instance.

    Raises:
        pydantic.ValidationError: If the merged configuration is invalid.
        KeyError: If the engine type is not registered.
    """
    if config is None:
        from config import load_config

        active_config = load_config(path)
    else:
        active_config = config
    engine_class = get_engine_class(active_config.search_engine.type)
    logger.debug(
        "Loading search engine",
        engine_type=active_config.search_engine.type,
        engine_class=engine_class.__name__,
    )
    return engine_class(active_config.search_engine, logger)
