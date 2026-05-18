"""HelpfulAssistantAgent definition."""

from ai_providers import BaseTool

from .base import BaseAgent


class HelpfulAssistantAgent(BaseAgent):
    """A helpful assistant agent."""

    system_prompt: str = "You are a helpful assistant."
    tools: list[BaseTool] = []
