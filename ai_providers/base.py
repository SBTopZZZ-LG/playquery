"""Base class for AI providers."""

import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypedDict, TypeVar

from pydantic import BaseModel


class JSONParseError(Exception):
    """Raised when the AI fails to return valid JSON after all retries."""


class BaseAIOptions(BaseModel):
    """Base Pydantic model for AI provider configuration options."""

    type: str
    """Provider type discriminator. Concrete subclasses narrow this to a ``Literal``."""


class ToolInvocation(TypedDict):
    """Invocation details passed to a tool handler by the model.

    Attributes:
        session_id: Identifier of the session that triggered the invocation.
        tool_call_id: Unique identifier for this specific tool call.
        tool_name: Name of the tool being invoked.
        arguments: Parsed arguments provided by the model for this call.
    """

    session_id: str
    tool_call_id: str
    tool_name: str
    arguments: Any


ToolResultType = Literal["success", "failure", "rejected", "denied"]


class ToolResult(TypedDict, total=False):
    """Result returned by a tool handler back to the model.

    Attributes:
        textResultForLlm: Text content returned to the model.
        resultType: Outcome classification of the tool call.
        error: Error message if the tool call failed.
        sessionLog: Human-readable log entry for the tool call.
    """

    textResultForLlm: str
    resultType: ToolResultType
    error: str
    sessionLog: str


ToolHandler = Callable[[ToolInvocation], ToolResult | Awaitable[ToolResult]]
"""Callable that handles a tool invocation.

Accepts a :class:`ToolInvocation` and returns either a :class:`ToolResult`
directly (sync) or an awaitable that resolves to one (async).
"""


@dataclass
class BaseTool:
    """Provider-agnostic tool definition.

    Attributes:
        name: Unique tool identifier recognised by the model.
        description: Natural-language description used by the model to decide
            when to invoke this tool.
        parameters: JSON Schema object describing the tool's accepted arguments.
        handler: Callable invoked when the model calls this tool. May be sync
            or async; receives a :class:`ToolInvocation` and must return a
            :class:`ToolResult`.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


T = TypeVar("T", bound=BaseAIOptions)


class BaseAIProvider(ABC, Generic[T]):
    """Abstract base class for AI providers."""

    options: T
    _system_prompt: str
    _tools: list[BaseTool]

    def __init__(self, options: T, *, system_prompt: str, tools: list[BaseTool]):
        """Initialize the base provider.

        Args:
            options: Provider options.
            system_prompt: System prompt passed to the model at session initialisation.
            tools: Provider-agnostic tool definitions to register with the session.
        """

        self.options = options
        self._system_prompt = system_prompt
        self._tools = tools

    @abstractmethod
    async def start(self) -> None:
        """Start the provider: establish connections and initialise the session.

        Raises:
            RuntimeError: If the provider fails to start.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the provider: tear down the session and release connections.

        Raises:
            RuntimeError: If cleanup fails.
        """

    @abstractmethod
    async def send_message_and_await_response(self, message: str) -> str:
        """Send a message to the AI provider and await a response.

        Args:
            message: Prompt content to send to the provider.

        Returns:
            Provider response text.

        Raises:
            Exception: Implementation-specific request/response failures.
        """

    async def query(self, user_message: str) -> str:
        """Send a message and return the raw response string.

        Args:
            user_message: Prompt content to send to the provider.

        Returns:
            Provider response text.
        """

        return await self.send_message_and_await_response(user_message)

    async def query_json(self, user_message: str, max_retries: int = 3) -> dict:
        """Send a message and return the response parsed as a dictionary.

        Retries up to ``max_retries`` times on JSON parse failure, sending
        the parse error back to the provider on each attempt.

        Args:
            user_message: Prompt content to send to the provider.
            max_retries: Maximum number of retry attempts on parse failure.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            JSONParseError: If the response cannot be parsed after all retries.
        """

        raw = await self.query(user_message)

        for attempt in range(max_retries + 1):
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                if attempt == max_retries:
                    raise JSONParseError(
                        f"Failed to parse JSON after {max_retries + 1} attempts. "
                        f"Last error: {exc}. Last response: {raw!r}"
                    ) from exc

                raw = await self.query(
                    f"Your previous response was not valid JSON. "
                    f"Parse error: {exc}. Please respond with valid JSON only."
                )
