"""Pydantic config models for the AI provider layer."""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from .copilot import CopilotAIOptions

# Extend this union as new provider implementations are added:
#   AIConfig = Annotated[
#       Union[CopilotAIOptions, OpenAIOptions, ...],
#       Field(discriminator="type"),
#   ]
AIConfig = Annotated[
    Union[CopilotAIOptions],  # noqa: UP007
    Field(discriminator="type"),
]
