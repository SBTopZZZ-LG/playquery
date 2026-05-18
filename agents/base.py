"""Base class for agent definitions."""

from abc import ABC

from ai_providers import BaseTool


class BaseAgent(ABC):
    """Base class for agent definitions.

    Subclasses declare the agent's identity as class-level attributes.

    Attributes:
        system_prompt: System prompt that establishes the agent's persona.
        tools: Tools the agent makes available to the model.
    """

    system_prompt: str
    tools: list[BaseTool]
