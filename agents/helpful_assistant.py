"""HelpfulAssistantAgent definition."""

from ai_providers import BaseTool
from tools.ping_pong import make_prefixed_ping_pong_tool, ping_pong
from .base import BaseAgent


class HelpfulAssistantAgent(BaseAgent):
    """A helpful assistant agent with ping-pong tool demonstrations."""

    system_prompt: str = "You are a helpful assistant."
    tools: list[BaseTool] = [
        ping_pong,
        make_prefixed_ping_pong_tool(prefix="[HelpfulAssistant]"),
    ]
