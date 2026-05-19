"""Logging interface and stdlib-backed implementation for PlayQuery."""

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, ParamSpec, TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel


class LoggingConfig(BaseModel):
    """Logging configuration for PlayQuery runtime output."""

    level: Literal["DEBUG"] = "DEBUG"


_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


class BaseLogger(ABC):
    """Minimal logging interface used across the application."""

    @abstractmethod
    def child(self, name: str) -> BaseLogger:
        """Return a child logger for a narrower component scope."""

    @abstractmethod
    def debug(self, message: str, **context: Any) -> None:
        """Emit a debug log message."""

    @abstractmethod
    def warning(self, message: str, **context: Any) -> None:
        """Emit a warning log message."""

    @abstractmethod
    def error(self, message: str, *, exc_info: BaseException | None = None, **context: Any) -> None:
        """Emit an error log message, optionally with traceback information."""


class StdlibLogger(BaseLogger):
    """Adapter that implements :class:`BaseLogger` using :mod:`logging`."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def child(self, name: str) -> BaseLogger:
        return StdlibLogger(self._logger.getChild(name))

    def debug(self, message: str, **context: Any) -> None:
        self._logger.debug(_format_message(message, context))

    def warning(self, message: str, **context: Any) -> None:
        self._logger.warning(_format_message(message, context))

    def error(self, message: str, *, exc_info: BaseException | None = None, **context: Any) -> None:
        self._logger.error(
            _format_message(message, context),
            exc_info=_build_exc_info(exc_info),
        )


def configure_logger(config: LoggingConfig, name: str = "playquery") -> BaseLogger:
    """Configure and return the application's root logger."""

    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_LOG_DATEFMT))

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(config.level)
    logger.propagate = False

    return StdlibLogger(logger)


def _format_context(context: dict[str, Any]) -> str:
    parts = [
        f"{key}={_sanitize_context_value(key, value)!r}" for key, value in sorted(context.items())
    ]
    return ", ".join(parts)


def _format_message(message: str, context: dict[str, Any]) -> str:
    if not context:
        return message
    return f"{message} | {_format_context(context)}"


def _build_exc_info(exc_info: BaseException | None):
    if exc_info is None:
        return None
    return (type(exc_info), exc_info, exc_info.__traceback__)


def _sanitize_context_value(key: str, value: Any) -> Any:
    if key in {"query", "user_message"}:
        return _summarize_text(value)
    if key in {"url", "final_url", "base_url"}:
        return _summarize_url(value)
    return value


def _summarize_text(value: Any) -> str:
    text = str(value)
    return f"<redacted len={len(text)}>"


def _summarize_url(value: Any) -> str:
    raw = str(value)
    parsed = urlsplit(raw)
    if not parsed.scheme and not parsed.netloc:
        return f"<redacted-url len={len(raw)}>"

    path_segments = len([segment for segment in parsed.path.split("/") if segment])
    return (
        f"<redacted-url scheme={parsed.scheme!r} host={parsed.netloc!r} "
        f"path_segments={path_segments}>"
    )


P = ParamSpec("P")
R = TypeVar("R")


def log_exceptions(
    message: str,
    *,
    logger_attr: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Log and re-raise exceptions from sync or async callables.

    The decorator looks for a logger in the wrapped callable's first argument
    via ``logger_attr`` or the conventional ``logger`` / ``_logger`` names.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if _is_async_callable(fn):

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    return await fn(*args, **kwargs)  # type: ignore
                except Exception as exc:
                    _log_exception(args, kwargs, message, exc, logger_attr)
                    raise

            return async_wrapper  # type: ignore

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                _log_exception(args, kwargs, message, exc, logger_attr)
                raise

        return sync_wrapper

    return decorator


def _is_async_callable(fn: Callable[..., Any]) -> bool:
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__  # type: ignore[attr-defined]
    return inspect.iscoroutinefunction(fn)


def _log_exception(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    message: str,
    exc: BaseException,
    logger_attr: str | None,
) -> None:
    logger = _resolve_logger(args, kwargs, logger_attr)
    if logger is None:
        return
    logger.error(message, exc_info=exc, error=str(exc), exception_type=type(exc).__name__)


def _resolve_logger(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    logger_attr: str | None,
) -> BaseLogger | None:
    candidate = kwargs.get("logger")
    if isinstance(candidate, BaseLogger):
        return candidate

    if not args:
        return None

    target = args[0]
    attrs = [logger_attr] if logger_attr is not None else ["logger", "_logger"]
    for attr in attrs:
        if attr is None:
            continue
        candidate = getattr(target, attr, None)
        if isinstance(candidate, BaseLogger):
            return candidate
    return None
