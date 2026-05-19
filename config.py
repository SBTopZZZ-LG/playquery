"""Root Pydantic config model, env-var resolution, and JSON Schema generation for PlayQuery."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ai_providers.config import AIConfig
from logger import LoggingConfig
from scraper.config import ScraperConfig
from search_engine.config import SearchEngineConfig


class PlayQueryConfig(BaseModel):
    """Root configuration model for playquery.yaml."""

    search_engine: SearchEngineConfig
    scraper: ScraperConfig | None = None
    ai: AIConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ---------------------------------------------------------------------------
# Env-var resolution
# ---------------------------------------------------------------------------


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _deep_set(d: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    for key in path[:-1]:
        d = d.setdefault(key, {})
    d[path[-1]] = value


# Each entry: (env_var_name, config_path_tuple, value_coercion_fn)
_ENV_MAP: list[tuple[str, tuple[str, ...], Callable[[str], Any]]] = [
    ("PLAYQUERY_LOGGING_LEVEL", ("logging", "level"), str),
    ("PLAYQUERY_SEARCH_ENGINE_TYPE", ("search_engine", "type"), str),
    ("PLAYQUERY_SEARCH_ENGINE_BASE_URL", ("search_engine", "base_url"), str),
    ("PLAYQUERY_SEARCH_ENGINE_USER_AGENT", ("search_engine", "user_agent"), str),
    ("PLAYQUERY_SEARCH_ENGINE_TIMEOUT", ("search_engine", "timeout"), float),
    ("PLAYQUERY_SCRAPER_TYPE", ("scraper", "type"), str),
    ("PLAYQUERY_SCRAPER_HEADLESS", ("scraper", "headless"), _parse_bool),
    ("PLAYQUERY_SCRAPER_CHANNEL", ("scraper", "channel"), str),
    ("PLAYQUERY_SCRAPER_LOCALE", ("scraper", "locale"), str),
    ("PLAYQUERY_SCRAPER_TIMEOUT", ("scraper", "timeout"), float),
    ("PLAYQUERY_AI_TYPE", ("ai", "type"), str),
    ("PLAYQUERY_AI_MODEL", ("ai", "model"), str),
    ("PLAYQUERY_AI_TIMEOUT", ("ai", "timeout"), float),
    ("PLAYQUERY_AI_GITHUB_TOKEN", ("ai", "github_token"), str),
]


def _build_env_overrides() -> dict[str, Any]:
    """Return a nested dict built from any set ``PLAYQUERY_*`` env vars."""
    overrides: dict[str, Any] = {}
    for env_var, path, coerce in _ENV_MAP:
        raw = os.environ.get(env_var)
        if raw is not None:
            _deep_set(overrides, path, coerce(raw))
    return overrides


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overrides* into a shallow copy of *base*."""
    result = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path = "playquery.yaml") -> PlayQueryConfig:
    """Load configuration with env vars taking precedence over the YAML file.

    Resolution order (highest priority first):
    1. ``PLAYQUERY_*`` environment variables
    2. ``playquery.yaml`` (or the file at *path*)
    3. Built-in defaults on each config model

    The YAML file is optional — if it does not exist, env vars and defaults
    are used, which is the expected mode when running inside Docker.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        A validated :class:`PlayQueryConfig` instance.

    Raises:
        pydantic.ValidationError: If the merged configuration is invalid.
    """
    yaml_data: dict[str, Any] = {}
    config_path = Path(path)
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    merged = _deep_merge(yaml_data, _build_env_overrides())
    return PlayQueryConfig.model_validate(merged)


if __name__ == "__main__":
    json.dump(PlayQueryConfig.model_json_schema(), sys.stdout, indent=2)
    sys.stdout.write("\n")
