"""Search engine base classes and interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel


class BaseSearchEngineOptions(BaseModel):
    """Base Pydantic model for search engine configuration options."""


@dataclass
class BaseEngineSearchOptions:
    """Base class for search options used in individual search calls."""


@dataclass
class SearchEngineResult:
    """Represents a single search result returned by the search engine."""

    title: str
    url: str
    category: str | None = None
    extra_info: dict[str, str] | None = None
    snippet: str | None = None


T = TypeVar("T", bound=BaseSearchEngineOptions)
R = TypeVar("R", bound=BaseEngineSearchOptions)


class BaseSearchEngine(ABC, Generic[T, R]):
    """Abstract base class for search engine implementations."""

    options: T

    def __init__(self, options: T):
        """Initialize the base search engine.

        Args:
            options: Search engine-specific options object.
        """

        self.options = options

    @abstractmethod
    def default_search_options(self) -> R:
        """Return a default per-search options instance for this engine."""

    @abstractmethod
    async def search(self, query: str, options: R) -> list[SearchEngineResult]:
        """
        Perform a search with the given query.

        Args:
            query: The search query string
            options: Search engine-specific options for this search

        Returns:
            A list of `SearchEngineResult` objects representing the search results.
        """
