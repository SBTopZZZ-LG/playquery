"""AI provider registry for the factory pattern."""

_REGISTRY: dict[str, type] = {}


def register_provider(type_id: str):
    """Class decorator that registers an AI provider implementation.

    Usage:
        @register_provider("copilot")
        class CopilotProvider(BaseAIProvider[CopilotAIOptions]):
            ...
    """

    def decorator(cls: type) -> type:
        _REGISTRY[type_id] = cls
        return cls

    return decorator


def get_provider_class(type_id: str) -> type:
    """Retrieve a registered AI provider class by its type identifier."""

    if type_id not in _REGISTRY:
        raise KeyError(
            f"No AI provider registered for type '{type_id}'. Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[type_id]
