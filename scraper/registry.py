"""Scraper registry for the factory pattern."""

_REGISTRY: dict[str, type] = {}


def register_scraper(type_id: str):
    """Class decorator that registers a scraper implementation.

    Usage:
        @register_scraper("patchright")
        class PatchrightScraper(BaseScraper[...]):
            ...
    """

    def decorator(cls: type) -> type:
        _REGISTRY[type_id] = cls
        return cls

    return decorator


def get_scraper_class(type_id: str) -> type:
    """Retrieve a registered scraper class by its type identifier."""

    if type_id not in _REGISTRY:
        raise KeyError(f"No scraper registered for type '{type_id}'. Available: {list(_REGISTRY)}")
    return _REGISTRY[type_id]
