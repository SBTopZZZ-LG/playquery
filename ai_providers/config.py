"""Pydantic config models for the AI provider layer."""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from .copilot import CopilotOptions
from .openai import OpenAIOptions

# Extend this union as new provider implementations are added:
#   AIConfig = Annotated[
#       Union[CopilotOptions, OpenAIOptions, ...],
#       Field(discriminator="type"),
#   ]
AIConfig = Annotated[
    Union[CopilotOptions, OpenAIOptions],  # noqa: UP007
    Field(discriminator="type"),
]
