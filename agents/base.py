"""Base class for agent definitions."""

from abc import ABC

from ai_providers import BaseTool


class BaseAgent(ABC):
    """Base class for agent definitions.

    Subclasses declare the agent's identity as class-level attributes.
    Callers pass these to :class:`~ai_providers.AIProviderConfig` when
    constructing a provider session.

    Attributes:
        system_prompt: System prompt that establishes the agent's persona.
        tools: Tools the agent makes available to the model.
    """

    system_prompt: str
    tools: list[BaseTool]
