"""SearXNG search engine implementation."""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import AnyHttpUrl
from searxng_search import (
    Category,
    FileResult,
    GeneralOrNewsResult,
    ImageResult,
    ITResult,
    MusicResult,
    SearXNG,
    SearXNGBaseConfiguration,
    SearXNGSearchConfiguration,
    SocialMediaResult,
    VideoResult,
)

from .base import (
    BaseSearchEngine,
    BaseSearchEngineOptions,
    BaseSearchOptions,
    SearchEngineResult,
)
from .registry import register_engine

ENGINE_TYPE = "searxng"

_EXTRA_FIELDS: dict[type, list[str]] = {
    GeneralOrNewsResult: ["author", "timestamp"],
    ITResult: ["author", "timestamp"],
    ImageResult: ["image_url", "thumbnail_url", "image_resolution"],
    VideoResult: ["video_thumbnail_url", "video_length", "author"],
    MusicResult: ["artist", "timestamp", "music_video_thumbnail_url"],
    FileResult: ["file_url", "file_thumbnail_url", "timestamp"],
    SocialMediaResult: ["thumbnail_url", "timestamp"],
}


class SearXNGOptions(BaseSearchEngineOptions):
    """Pydantic model for SearXNG engine configuration."""

    type: Literal[ENGINE_TYPE] = ENGINE_TYPE  # type: ignore[valid-type]
    base_url: AnyHttpUrl
    user_agent: str | None = None
    timeout: float | None = 30.0


@dataclass
class SearXNGSearchOptions(BaseSearchOptions):
    """Search options specific to SearXNG searches."""

    categories: set[Category | str] | None = None
    enabled_engines: set[str] | None = None
    disabled_engines: set[str] | None = None
    custom_params: dict[str, str] | None = None
    custom_headers: dict[str, str] | None = None


def _build_extra(result: Any) -> dict[str, str] | None:
    keys = _EXTRA_FIELDS.get(type(result), [])
    extra = {k: v for k in keys if (v := getattr(result, k, None)) is not None}
    return extra or None


def _to_search_engine_result(result: Any) -> SearchEngineResult:
    return SearchEngineResult(
        title=result.title,
        url=str(result.url),
        category=result.category,
        snippet=result.description,
        extra_info=_build_extra(result),
    )


@register_engine(ENGINE_TYPE)
class SearXNGSearchEngine(BaseSearchEngine[SearXNGOptions, SearXNGSearchOptions]):
    """SearXNG search engine implementation."""

    def default_search_options(self) -> SearXNGSearchOptions:
        return SearXNGSearchOptions()

    async def search(self, query: str, options: SearXNGSearchOptions) -> list[SearchEngineResult]:
        self.logger.debug(
            "Executing SearXNG search",
            query=query,
            base_url=str(self.options.base_url),
        )
        base_config = SearXNGBaseConfiguration(
            base_url=str(self.options.base_url),
            user_agent=self.options.user_agent,
            timeout=self.options.timeout,
            handle_rate_limiting=True,
        )
        search_config = SearXNGSearchConfiguration(
            query=query,
            categories=options.categories,
            enabled_engines=options.enabled_engines,
            disabled_engines=options.disabled_engines,
            custom_params=options.custom_params,
            custom_headers=options.custom_headers,
        )
        client = SearXNG(base_configuration=base_config)
        response = await client.search(search_configuration=search_config)
        results = [_to_search_engine_result(r) for r in response.search_results]
        self.logger.debug("SearXNG search completed", query=query, result_count=len(results))
        return results
