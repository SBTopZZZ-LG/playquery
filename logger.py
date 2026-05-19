"""Logging interface and stdlib-backed implementation for PlayQuery."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Literal

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


class StdlibLogger(BaseLogger):
    """Adapter that implements :class:`BaseLogger` using :mod:`logging`."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def child(self, name: str) -> BaseLogger:
        return StdlibLogger(self._logger.getChild(name))

    def debug(self, message: str, **context: Any) -> None:
        if context:
            self._logger.debug("%s | %s", message, _format_context(context))
            return

        self._logger.debug(message)


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
    parts = [f"{key}={value!r}" for key, value in sorted(context.items())]
    return ", ".join(parts)
