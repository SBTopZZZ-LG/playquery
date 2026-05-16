"""Copilot AI provider implementation."""


from dataclasses import dataclass, field
from typing import Optional, cast
from copilot import CopilotClient, CopilotSession, SessionConfig, Tool
from copilot import ToolHandler as SDKToolHandler

from .base import BaseAIProvider, BaseAIProviderOptions, BaseTool


@dataclass
class CopilotProviderOptions(BaseAIProviderOptions):
    """Options for initializing the Copilot provider.

    Attributes:
        client: Connected Copilot client instance.
        model: Model identifier used when creating sessions.
        system_prompt: System prompt passed to the model as the initial system message.
        timeout: Timeout in seconds for send-and-wait operations.
        tools: Provider-agnostic tool definitions registered with the session.
            Each ``BaseTool`` is mapped to a Copilot SDK ``Tool`` at session creation.
    """

    client: CopilotClient
    model: str = "gpt-4o"
    system_prompt: str = "You are a helpful assistant."
    timeout: float = 1800
    tools: list[BaseTool] = field(default_factory=list)


class CopilotProvider(BaseAIProvider[CopilotProviderOptions]):
    """Copilot AI provider implementation.

    Args:
        options: Copilot provider options including client, model, system_prompt, and timeout.
    """

    session: Optional[CopilotSession]

    def __init__(self, options: CopilotProviderOptions):
        """Initialize the Copilot provider.

        Args:
            options: Copilot provider options.
        """

        super().__init__(options)
        self.session = None

    async def initialize_session(self):
        """Initialize a Copilot session for the configured model and system prompt.

        The system prompt is passed to the SDK as a system message with mode ``replace``
        so it takes effect for the full duration of the session.

        Each ``BaseTool`` in ``options.tools`` is mapped to a Copilot SDK ``Tool``
        before the session is created. If no tools are provided the ``tools`` key is
        omitted from the session payload entirely.

        Returns:
            None

        Raises:
            ValueError: If client, model, or timeout configuration is invalid.
            RuntimeError: If the Copilot SDK fails to create a session.
        """

        options = self.options

        if options.client is None:
            raise ValueError(
                "Copilot client must be provided for session initialization.")
        if options.client.get_state() != 'connected':
            raise ValueError(
                "Copilot client must be connected to initialize session.")
        if options.model is None or str.strip(options.model) == "":
            raise ValueError(
                "Valid model name must be provided for session initialization.")
        if options.timeout <= 0:
            raise ValueError(
                "Timeout must be a positive floating point number for session initialization.")

        if self.session is not None:
            print("Warning: Copilot session already initialized. Reinitializing session.")
            await self.dispose_session()

        sdk_tools = [
            Tool(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
                handler=cast(SDKToolHandler, t.handler),
            )
            for t in options.tools
        ]

        session_config: SessionConfig = {
            "model": options.model,
            "system_message": {
                "content": options.system_prompt,
                "mode": "replace"
            },
        }
        if sdk_tools:
            session_config["tools"] = sdk_tools

        self.session = await options.client.create_session(session_config)

    async def send_message_and_await_response(self, message: str) -> str:
        """Send a prompt and wait for a Copilot response.

        Args:
            message: Prompt content to send to the active session.

        Returns:
            Response content text. Returns an empty string when no content is present.

        Raises:
            ValueError: If no session is initialized.
            RuntimeError: If the SDK returns an invalid or empty response payload.
        """

        if self.session is None:
            raise ValueError("Copilot session is not initialized.")

        response = await self.session.send_and_wait(
            {"prompt": message},
            timeout=self.options.timeout
        )

        if response is None:
            raise RuntimeError("Received null response from Copilot session.")
        if response.data is None:
            raise RuntimeError(
                "Received response with null data from Copilot session.")

        return response.data.content or ""

    async def dispose_session(self):
        """Dispose the active Copilot session.

        Returns:
            None

        Raises:
            RuntimeError: If session destruction fails.
        """

        if self.session is None:
            return

        try:
            await self.session.destroy()
        except Exception as e:
            raise RuntimeError(
                f"Failed to dispose Copilot session: {str(e)}") from e
        finally:
            self.session = None
