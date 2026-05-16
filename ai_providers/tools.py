"""
Tool definition utilities for the ai_providers package.

Provides a decorator-based API for defining :class:`BaseTool` instances with
automatic JSON Schema generation from Pydantic models.

Usage — decorator form (recommended)::

    from pydantic import BaseModel, Field
    from ai_providers import define_tool

    class LookupParams(BaseModel):
        id: str = Field(description="Issue identifier")

    @define_tool(description="Fetch issue details from the tracker")
    def lookup_issue(params: LookupParams) -> str:
        return fetch_issue(params.id).summary

Usage — function form::

    tool = define_tool(
        "lookup_issue",
        description="Fetch issue details from the tracker",
        handler=lambda params: fetch_issue(params["id"]).summary,
    )
"""

from __future__ import annotations

import inspect
import typing
from typing import Any, Callable, TypeVar, overload

from .base import BaseTool, ToolInvocation, ToolResult

try:
    from pydantic import BaseModel as _BaseModel
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _BaseModel = None
    _PYDANTIC_AVAILABLE = False

_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_pydantic(t: Any) -> bool:
    """Return True if *t* is a Pydantic BaseModel subclass."""
    if not _PYDANTIC_AVAILABLE or _BaseModel is None:
        return False
    try:
        return isinstance(t, type) and issubclass(t, _BaseModel)
    except TypeError:
        return False


def _normalize_result(result: Any) -> ToolResult:
    """Coerce any handler return value to a :class:`ToolResult` dict.

    - ``None``                → empty success result
    - ``str``                 → ``textResultForLlm`` success result
    - ``dict``                → returned as-is (assumed to be ToolResult)
    - Pydantic ``BaseModel``  → JSON-serialized success result
    - Anything else           → ``str(result)`` success result
    """
    if result is None:
        return {"textResultForLlm": "", "resultType": "success"}
    if isinstance(result, str):
        return {"textResultForLlm": result, "resultType": "success"}
    if isinstance(result, dict):
        return result  # type: ignore[return-value]
    if _PYDANTIC_AVAILABLE and _BaseModel is not None and isinstance(result, _BaseModel):
        return {"textResultForLlm": result.model_dump_json(), "resultType": "success"}
    return {"textResultForLlm": str(result), "resultType": "success"}


def _get_type_hints_safe(fn: Callable[..., Any]) -> dict[str, Any]:
    """Return type hints for *fn*, silently returning an empty dict on failure."""

    try:
        return typing.get_type_hints(fn)
    except NameError:
        return {}
    except AttributeError:
        return {}


def _detect_signature(
    fn: Callable[..., Any],
    ptype_override: type | None,
) -> tuple[bool, bool, type | None]:
    """Inspect *fn* and return ``(takes_params, takes_invocation, ptype)``."""
    hints = _get_type_hints_safe(fn)
    param_names = list(inspect.signature(fn).parameters)
    num_params = len(param_names)
    first_hint = hints.get(param_names[0]) if param_names else None

    if num_params == 0:
        return False, False, ptype_override
    if num_params == 1 and first_hint is ToolInvocation:
        return False, True, ptype_override

    takes_invocation = num_params >= 2
    ptype = ptype_override
    if ptype is None and _is_pydantic(first_hint):
        ptype = first_hint
    return True, takes_invocation, ptype


def _resolve_call_args(
    invocation: ToolInvocation,
    takes_params: bool,
    takes_invocation: bool,
    ptype: type | None,
) -> list[Any]:
    """Build the positional argument list for a tool handler call."""
    call_args: list[Any] = []
    if takes_params:
        raw_args = invocation.get("arguments") or {}
        if ptype is not None and _is_pydantic(ptype):
            call_args.append(
                ptype.model_validate(raw_args)
            )
        else:
            call_args.append(raw_args)
    if takes_invocation:
        call_args.append(invocation)
    return call_args


def _build_handler(
    fn: Callable[..., Any],
    ptype: type | None,
) -> Callable[[ToolInvocation], Any]:
    """Wrap a user function in the :data:`ToolHandler` calling convention.

    Detects the function's signature via :func:`_detect_signature` and builds
    an async wrapper that validates/unpacks params, normalises the return value
    to :class:`ToolResult`, and catches handler exceptions so the model
    receives a safe error message rather than a raw traceback.
    """
    takes_params, takes_invocation, resolved_ptype = _detect_signature(
        fn, ptype)

    async def _handler(invocation: ToolInvocation) -> ToolResult:
        try:
            call_args = _resolve_call_args(
                invocation, takes_params, takes_invocation, resolved_ptype
            )
            result = fn(*call_args)
            if inspect.isawaitable(result):
                result = await result
            return _normalize_result(result)
        except (ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return {
                "textResultForLlm": "Invoking this tool produced an error.",
                "resultType": "failure",
                "error": str(exc),
            }

    return _handler


def _schema_from_hints(fn: Callable[..., Any]) -> tuple[dict[str, Any] | None, type | None]:
    """Derive JSON Schema and Pydantic type from the function's first parameter."""
    hints = _get_type_hints_safe(fn)
    param_names = list(inspect.signature(fn).parameters)
    if not param_names:
        return None, None

    first_hint = hints.get(param_names[0])
    if _is_pydantic(first_hint):
        schema: dict[str, Any] = first_hint.model_json_schema()  # type: ignore
        return schema, first_hint

    return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@overload
def define_tool(
    name: str | None = None,
    *,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], BaseTool]: ...


@overload
def define_tool(
    name: str,
    *,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
    handler: Callable[..., Any],
) -> BaseTool: ...


def define_tool(
    name: str | None = None,
    *,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
    handler: Callable[..., Any] | None = None,
) -> BaseTool | Callable[[Callable[..., Any]], BaseTool]:
    """Define a :class:`BaseTool` from a plain function.

    Can be used as a decorator or as a plain function call.

    **Decorator usage** (recommended)::

        class PingParams(BaseModel):
            value: str = Field(description="Value to echo")

        @define_tool(description="Echo value as pong")
        def ping_pong(params: PingParams) -> str:
            return f"pong: {params.value}"

    **Function usage**::

        tool = define_tool(
            "ping_pong",
            description="Echo value as pong",
            handler=lambda params: f"pong: {params['value']}",
        )

    Args:
        name: Tool name exposed to the model. Defaults to the function name.
        description: Natural-language description shown to the model.
        parameters: Explicit JSON Schema for the tool's arguments. When
            omitted and the function's first parameter is a Pydantic model,
            the schema is generated automatically.
        handler: Function to wrap (for the non-decorator call form). Requires
            *name* to be set explicitly.

    Returns:
        A :class:`BaseTool` instance (or a decorator that returns one).

    Raises:
        ValueError: When *handler* is provided but *name* is omitted.
    """

    def decorator(fn: Callable[..., Any]) -> BaseTool:
        tool_name = name if name is not None else getattr(
            fn, "__name__", "unknown_tool")

        # Resolve schema: explicit > Pydantic auto-generation > empty object
        schema = parameters
        ptype: type | None = None
        if schema is None:
            schema, ptype = _schema_from_hints(fn)
        if schema is None:
            schema = {"type": "object", "properties": {}}

        return BaseTool(
            name=tool_name,
            description=description or "",
            parameters=schema,
            handler=_build_handler(fn, ptype),
        )

    if handler is not None:
        if name is None:
            raise ValueError(
                "'name' is required when using define_tool with 'handler='.")
        return decorator(handler)

    return decorator
