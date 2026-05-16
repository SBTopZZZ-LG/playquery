"""AI Providers package."""

from .base import BaseAIProvider, BaseAIProviderOptions, \
    BaseTool, JSONParseError, ToolHandler, ToolInvocation, ToolResult, ToolResultType
from .copilot import CopilotProvider, CopilotProviderOptions
from .factory import AIProviderConfig, ProviderType, \
    create_ai_provider, dispose_ai_provider, managed_ai_provider
from .tools import define_tool

__all__ = [
    "AIProviderConfig",
    "BaseAIProvider",
    "BaseAIProviderOptions",
    "BaseTool",
    "JSONParseError",
    "CopilotProvider",
    "CopilotProviderOptions",
    "ProviderType",
    "ToolHandler",
    "ToolInvocation",
    "ToolResult",
    "ToolResultType",
    "create_ai_provider",
    "define_tool",
    "dispose_ai_provider",
    "managed_ai_provider"
]
