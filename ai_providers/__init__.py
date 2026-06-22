"""AI provider implementations."""

from .base import (
    BaseAIOptions,
    BaseAIProvider,
    BaseTool,
    JSONParseError,
    ToolHandler,
    ToolInvocation,
    ToolResult,
    ToolResultType,
)
from .config import AIConfig
from .copilot import CopilotOptions, CopilotProvider
from .factory import (
    create_ai_provider,
    dispose_ai_provider,
    managed_ai_provider,
)
from .openai import OpenAIOptions, OpenAIProvider
from .registry import get_provider_class, register_provider
from .tools import define_tool

__all__ = [
    "AIConfig",
    "BaseAIOptions",
    "BaseAIProvider",
    "BaseTool",
    "JSONParseError",
    "CopilotOptions",
    "CopilotProvider",
    "OpenAIOptions",
    "OpenAIProvider",
    "ToolHandler",
    "ToolInvocation",
    "ToolResult",
    "ToolResultType",
    "create_ai_provider",
    "define_tool",
    "dispose_ai_provider",
    "get_provider_class",
    "managed_ai_provider",
    "register_provider",
]
