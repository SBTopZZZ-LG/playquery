"""OpenAI AI provider implementation via OpenAI-compatible API."""

import inspect
import json
import os
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import Field

from logger import BaseLogger, log_exceptions

from .base import BaseAIOptions, BaseAIProvider, BaseTool
from .registry import register_provider


class OpenAIOptions(BaseAIOptions):
    """Pydantic model for OpenAI AI provider configuration."""

    type: Literal["openai"] = "openai"  # type: ignore[assignment]

    api_key: str = Field(default_factory=lambda: os.environ.get("PLAYQUERY_AI_API_KEY", ""))
    """API key for authenticating with the OpenAI API. Falls back to PLAYQUERY_AI_API_KEY env var."""

    base_url: str = "https://api.openai.com/v1"
    """Base URL for the OpenAI-compatible API endpoint."""

    model: str = "gpt-4o"
    """Model identifier used for chat completions."""

    timeout: float = 60.0
    """Timeout in seconds for API requests."""


@register_provider("openai")
class OpenAIProvider(BaseAIProvider[OpenAIOptions]):
    """OpenAI AI provider implementation via OpenAI-compatible API."""

    _client: AsyncOpenAI
    _messages: list[dict[str, Any]]

    def __init__(
        self,
        options: OpenAIOptions,
        *,
        logger: BaseLogger,
        system_prompt: str,
        tools: list[BaseTool],
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            options: OpenAI provider options.
            logger: Component logger instance.
            system_prompt: System prompt passed to the model.
            tools: Tool definitions to register with the session.
        """

        super().__init__(options, logger=logger, system_prompt=system_prompt, tools=tools)
        self._client = AsyncOpenAI(
            api_key=options.api_key,
            base_url=options.base_url,
            timeout=options.timeout,
        )
        self._messages = []

    @log_exceptions("OpenAI provider start failed", logger_attr="logger")
    async def start(self) -> None:
        """Initialise the message history for an OpenAI chat session.

        Sets up the initial system message from the configured system prompt.

        Raises:
            ValueError: If model or timeout configuration is invalid.
        """

        if not self.options.model.strip():
            raise ValueError("Valid model name must be provided for session initialization.")
        if self.options.timeout <= 0:
            raise ValueError("Timeout must be a positive floating point number.")

        if self._messages:
            self.logger.warning("OpenAI session already initialized; reinitializing")
            await self._dispose_session()

        self._messages = [{"role": "system", "content": self._system_prompt}]

    @log_exceptions("OpenAI provider stop failed", logger_attr="logger")
    async def stop(self) -> None:
        """Dispose the active OpenAI session by clearing message history."""

        await self._dispose_session()

    async def _dispose_session(self) -> None:
        """Clear message history."""
        self._messages = []

    @log_exceptions("OpenAI request failed", logger_attr="logger")
    async def send_message_and_await_response(self, message: str) -> str:
        """Send a prompt and wait for an OpenAI response.

        Handles tool call loops automatically: when the model requests tool
        invocations, the corresponding handlers are called and results are
        fed back until the model produces a final text response.

        Args:
            message: Prompt content to send to the active session.

        Returns:
            Response content text. Returns an empty string when no content is present.

        Raises:
            ValueError: If no session is initialized.
            RuntimeError: If the API returns an invalid or empty response.
        """

        if not self._messages:
            raise ValueError("OpenAI session is not initialized.")

        self._messages.append({"role": "user", "content": message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools
        ]

        while True:
            kwargs: dict[str, Any] = {
                "model": self.options.model,
                "messages": self._messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self._client.chat.completions.create(**kwargs)

            if response is None or not response.choices:
                raise RuntimeError("Received empty response from OpenAI API.")

            msg = response.choices[0].message

            if msg.tool_calls:
                self._messages.append({"role": "assistant", "content": msg.content or ""})
                for tc in msg.tool_calls:
                    tc_id = tc.id or ""
                    tc_name = tc.function.name or ""
                    tc_args = json.loads(tc.function.arguments or "{}")
                    result = self._tools[
                        next(i for i, t in enumerate(self._tools) if t.name == tc_name)
                    ].handler(
                        {
                            "session_id": "",
                            "tool_call_id": tc_id,
                            "tool_name": tc_name,
                            "arguments": tc_args,
                        }
                    )
                    if inspect.isawaitable(result):
                        result = await result

                    self._messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result.get("textResultForLlm", ""),
                        }
                    )
                continue

            assistant_content = msg.content or ""
            self._messages.append({"role": "assistant", "content": assistant_content})
            self.logger.debug("Received response from OpenAI", response_length=len(assistant_content))
            return assistant_content
