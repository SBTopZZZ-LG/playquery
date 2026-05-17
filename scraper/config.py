"""Pydantic config models for the scraper layer."""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from .patchright import PatchrightOptions

# Extend this union as new scraper implementations are added:
#   ScraperConfig = Annotated[
#       Union[PatchrightOptions, SomeOtherOptions, ...],
#       Field(discriminator="type"),
#   ]
ScraperConfig = Annotated[
    Union[PatchrightOptions],  # noqa: UP007
    Field(discriminator="type"),
]
