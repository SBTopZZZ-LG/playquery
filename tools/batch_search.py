"""Batch-search tool builder."""

import dataclasses

from pydantic import Field

from ai_providers import BaseTool, define_tool
from core.service import PlayQueryService
from search_engine.base import SearchEngineResult

from ._utils import make_params_model, sanitize_schema


def make_batch_search_tool(service: PlayQueryService) -> BaseTool:
    """Return a batch-search tool bound to *service*.

    The tool accepts a list of query strings and runs all of them in parallel,
    returning a mapping of query → results.  The parameter schema is derived
    dynamically from the engine's concrete search-options dataclass.
    """
    options_type = type(service._engine.default_search_options())  # pylint: disable=protected-access

    primary = {
        "queries": (
            list[str],
            Field(description="List of search query strings to run in parallel."),
        ),
        "max_results": (
            int,
            Field(default=10, description="Maximum number of results to return per query."),
        ),
    }
    batch_search_params = make_params_model("BatchSearchParams", primary, options_type)

    async def _handler(params) -> dict[str, list[SearchEngineResult]]:  # type: ignore[no-untyped-def]
        engine_options = {f.name: getattr(params, f.name) for f in dataclasses.fields(options_type)}
        return await service.batch_search(params.queries, params.max_results, engine_options)

    _handler.__annotations__ = {
        "params": batch_search_params,
        "return": dict[str, list[SearchEngineResult]],
    }

    tool = define_tool(
        name="batch_search",
        description=(
            "Run multiple search queries in parallel and return results per query. "
            "Returns a dict mapping each query string to its list of search results. "
            "Use this when you need to research several distinct sub-topics at once "
            "and want to avoid sequential round-trips. Always pass all queries in a "
            "single call; never call this tool in a loop for individual queries."
        ),
    )(_handler)
    tool.parameters = sanitize_schema(tool.parameters)
    return tool
