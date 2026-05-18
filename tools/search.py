"""Search tool builder."""

import dataclasses

from pydantic import Field

from ai_providers import BaseTool, define_tool
from core.service import PlayQueryService
from search_engine.base import SearchEngineResult

from ._utils import make_params_model


def make_search_tool(service: PlayQueryService) -> BaseTool:
    """Return a search tool bound to *service*.

    The tool's parameter schema is derived dynamically from the engine's
    concrete search-options dataclass, so the agent always sees the exact
    set of options the configured engine supports.

    # TODO (post-MVP): expose Google-dork style parameters (e.g. site:, filetype:)
    # as first-class fields when the engine is a Google-backed implementation.
    """
    options_type = type(service._engine.default_search_options())

    primary = {
        "query": (str, Field(description="The search query string.")),
        "max_results": (int, Field(default=10, description="Maximum number of results to return.")),
    }
    SearchParams = make_params_model("SearchParams", primary, options_type)

    async def _handler(params) -> list[SearchEngineResult]:  # type: ignore[no-untyped-def]
        engine_options = {f.name: getattr(params, f.name) for f in dataclasses.fields(options_type)}
        return await service.search(params.query, params.max_results, engine_options)

    _handler.__annotations__ = {"params": SearchParams, "return": list[SearchEngineResult]}

    return define_tool(description="Search the web and return a list of results.")(_handler)
