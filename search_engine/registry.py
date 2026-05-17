"""Search engine registry for the factory pattern."""

_REGISTRY: dict[str, type] = {}


def register_engine(type_id: str):
    """Class decorator that registers a search engine implementation.

    Usage:
        @register_engine("searxng")
        class SearXNGSearchEngine(BaseSearchEngine[...]):
            ...
    """

    def decorator(cls: type) -> type:
        _REGISTRY[type_id] = cls
        return cls

    return decorator


def get_engine_class(type_id: str) -> type:
    """Retrieve a registered search engine class by its type identifier."""

    if type_id not in _REGISTRY:
        raise KeyError(
            f"No search engine registered for type '{type_id}'. Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[type_id]
