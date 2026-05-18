"""AI Providers package."""

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
from .copilot import CopilotAIOptions, CopilotProvider
from .factory import (
    create_ai_provider,
    dispose_ai_provider,
    managed_ai_provider,
)
from .registry import get_provider_class, register_provider
from .tools import define_tool

__all__ = [
    "AIConfig",
    "BaseAIOptions",
    "BaseAIProvider",
    "BaseTool",
    "JSONParseError",
    "CopilotAIOptions",
    "CopilotProvider",
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
