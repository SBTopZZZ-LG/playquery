"""Search engine implementations."""

from .base import (
    BaseSearchEngine,
    BaseSearchEngineOptions,
    BaseSearchOptions,
    SearchEngineResult,
)
from .config import SearchEngineConfig
from .factory import load_engine
from .registry import get_engine_class, register_engine
from .searxng import SearXNGOptions, SearXNGSearchEngine, SearXNGSearchOptions

__all__ = [
    "BaseSearchOptions",
    "BaseSearchEngine",
    "BaseSearchEngineOptions",
    "SearchEngineResult",
    "SearchEngineConfig",
    "load_engine",
    "get_engine_class",
    "register_engine",
    "SearXNGOptions",
    "SearXNGSearchEngine",
    "SearXNGSearchOptions",
]
