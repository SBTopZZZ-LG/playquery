"""Copilot AI provider implementation."""

import inspect
from typing import Any, Literal

import copilot
from copilot import CopilotClient, CopilotSession
from copilot.generated.session_events import AssistantMessageData
from copilot.session import PermissionHandler, SessionConfig
from copilot.tools import Tool
from copilot.tools import ToolInvocation as SDKToolInvocation
from copilot.tools import ToolResult as SDKToolResult
from pydantic import Field

from .base import BaseAIOptions, BaseAIProvider, BaseTool
from .registry import register_provider


class CopilotAIOptions(BaseAIOptions):
    """Pydantic model for Copilot AI provider configuration."""

    type: Literal["copilot"] = "copilot"  # type: ignore[assignment]

    model: str = "claude-sonnet-4.6"
    """Model name to use for the session. Defaults to 'claude-sonnet-4.6'."""

    timeout: float = 300.0
    """Default timeout in seconds for model responses. Defaults to 300 seconds (5 minutes)."""

    github_token: str | None = Field(default=None)
    """GitHub personal access token for Copilot authentication.
    Set via ``PLAYQUERY_AI_GITHUB_TOKEN``. Falls back to the SDK's built-in
    auth (CLI / device flow) when ``None``."""


def _make_sdk_handler(tool: BaseTool):
    """Wrap a :class:`BaseTool` handler for the Copilot SDK calling convention.

    Adapts between the SDK's ``ToolInvocation`` dataclass / ``ToolResult``
    dataclass and our internal ``ToolInvocation`` TypedDict / ``ToolResult``
    TypedDict so that our generic tool layer doesn't need to know about SDK
    internals.
    """

    async def _handler(sdk_inv: SDKToolInvocation) -> SDKToolResult:
        our_inv: Any = {
            "session_id": sdk_inv.session_id,
            "tool_call_id": sdk_inv.tool_call_id,
            "tool_name": sdk_inv.tool_name,
            "arguments": sdk_inv.arguments,
        }
        try:
            result = tool.handler(our_inv)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # pylint: disable=broad-except
            return SDKToolResult(
                text_result_for_llm="Tool execution raised an unexpected error.",
                result_type="failure",
                error=str(exc),
            )

        # result is our ToolResult TypedDict (camelCase keys)
        return SDKToolResult(
            text_result_for_llm=result.get("textResultForLlm", ""),
            result_type=result.get("resultType", "success"),
            error=result.get("error"),
        )

    return _handler


@register_provider("copilot")
class CopilotProvider(BaseAIProvider[CopilotAIOptions]):
    """Copilot AI provider implementation."""

    _client: CopilotClient | None
    _session: CopilotSession | None

    def __init__(self, options: CopilotAIOptions, *, system_prompt: str, tools: list[BaseTool]):
        """Initialize the Copilot provider.

        Args:
            options: Copilot provider options.
            system_prompt: System prompt passed to the model at session initialisation.
            tools: Tool definitions to register with the session.
        """

        super().__init__(options, system_prompt=system_prompt, tools=tools)
        self._client = None
        self._session = None

    async def start(self) -> None:
        """Create and connect the Copilot client, then initialise a session.

        Raises:
            RuntimeError: If the client fails to start.
        """

        self._client = copilot.CopilotClient(
            config=copilot.SubprocessConfig(github_token=self.options.github_token)
        )
        try:
            await self._client.start()
        except Exception as e:
            raise RuntimeError(f"Failed to start Copilot client: {e}") from e

        await self._initialize_session()

    async def stop(self) -> None:
        """Dispose the session and stop the Copilot client.

        Raises:
            RuntimeError: If client teardown fails.
        """

        await self._dispose_session()
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as e:
                raise RuntimeError(f"Failed to stop Copilot client: {e}") from e
            finally:
                self._client = None

    async def _initialize_session(self) -> None:
        """Initialise a Copilot session. Called internally by :meth:`start`.

        Raises:
            ValueError: If the client is not connected or options are invalid.
            RuntimeError: If the Copilot SDK fails to create a session.
        """

        if self._client is None or self._client.get_state() != "connected":
            raise ValueError("Copilot client must be connected before initialising a session.")
        if not self.options.model.strip():
            raise ValueError("A non-empty model name is required.")
        if self.options.timeout <= 0:
            raise ValueError("Timeout must be a positive number.")

        if self._session is not None:
            print("Warning: Copilot session already initialised. Reinitialising.")
            await self._dispose_session()

        sdk_tools = [
            Tool(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
                handler=_make_sdk_handler(t),
            )
            for t in self._tools
        ]

        session_config: SessionConfig = {
            "model": self.options.model,
            "system_message": {"content": self._system_prompt, "mode": "replace"},
            "on_permission_request": PermissionHandler.approve_all,
        }
        if sdk_tools:
            session_config["tools"] = sdk_tools

        self._session = await self._client.create_session(**session_config)

    async def _dispose_session(self) -> None:
        """Destroy the active session. Called internally by :meth:`stop`."""

        if self._session is None:
            return
        try:
            await self._session.destroy()
        except Exception as e:
            raise RuntimeError(f"Failed to dispose Copilot session: {e}") from e
        finally:
            self._session = None

    async def send_message_and_await_response(self, message: str) -> str:
        """Send a prompt and wait for a Copilot response.

        Args:
            message: Prompt content to send to the active session.

        Returns:
            Response content text. Returns an empty string when no content is present.

        Raises:
            ValueError: If no session is initialised.
            RuntimeError: If the SDK returns an invalid or empty response payload.
        """

        if self._session is None:
            raise ValueError("Copilot session is not initialised.")

        response = await self._session.send_and_wait(message, timeout=self.options.timeout)

        if response is None:
            raise RuntimeError("Received null response from Copilot session.")
        if response.data is None:
            raise RuntimeError("Received response with null data from Copilot session.")

        response_content = ""
        if isinstance(response.data, AssistantMessageData):
            response_content = response.data.content or ""

        return response_content
