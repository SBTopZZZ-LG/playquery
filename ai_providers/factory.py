"""Factory for creating AI provider instances based on configuration."""

from contextlib import asynccontextmanager

from .base import BaseAIOptions, BaseAIProvider, BaseTool
from .registry import get_provider_class


def create_ai_provider(
    options: BaseAIOptions,
    *,
    system_prompt: str,
    tools: list[BaseTool],
) -> BaseAIProvider:
    """Create an AI provider instance from configuration options.

    The returned provider is **not yet started**. Call :meth:`~BaseAIProvider.start`
    before querying, or use :func:`managed_ai_provider` which handles the full lifecycle.

    Args:
        options: Provider options. The ``type`` field determines which registered
            implementation is instantiated.
        system_prompt: System prompt passed to the model at session initialisation.
        tools: Provider-agnostic tool definitions to register with the session.

    Returns:
        An unstarted provider instance.

    Raises:
        KeyError: If no provider is registered for ``options.type``.
    """

    provider_class = get_provider_class(options.type)
    return provider_class(options, system_prompt=system_prompt, tools=tools)


async def dispose_ai_provider(provider: BaseAIProvider) -> None:
    """Stop a provider and release all its resources.

    Args:
        provider: Provider instance to dispose.
    """

    await provider.stop()


@asynccontextmanager
async def managed_ai_provider(
    options: BaseAIOptions,
    *,
    system_prompt: str,
    tools: list[BaseTool],
):
    """Async context manager that manages the full provider lifecycle.

    Starts the provider on entry and stops it on exit (including on exception).

    Args:
        options: Provider options.
        system_prompt: System prompt passed to the model at session initialisation.
        tools: Provider-agnostic tool definitions to register with the session.

    Yields:
        A started :class:`BaseAIProvider` instance ready for use.

    Raises:
        KeyError: If no provider is registered for ``options.type``.
        RuntimeError: If provider startup or teardown fails.
    """

    provider = create_ai_provider(options, system_prompt=system_prompt, tools=tools)
    try:
        await provider.start()
        yield provider
    finally:
        await provider.stop()
