"""Pydantic config models for the search engine layer."""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from .searxng import SearXNGOptions

# Extend this union as new engine implementations are added:
#   SearchEngineConfig = Annotated[
#       Union[SearXNGOptions, SerperOptions, ...],
#       Field(discriminator="type"),
#   ]
SearchEngineConfig = Annotated[
    Union[SearXNGOptions],  # noqa: UP007
    Field(discriminator="type"),
]
