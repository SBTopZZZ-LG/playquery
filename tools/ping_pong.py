"""Ping-pong tool definitions.

Demonstrates both tool definition patterns:

- **Stateless** — ``ping_pong`` is a pure, dependency-free tool defined at
  module level with ``@define_tool``. Import and use it directly.

- **Stateful (factory)** — ``make_prefixed_ping_pong_tool`` accepts a runtime
  dependency (``prefix: str``) and returns a :class:`~ai_providers.BaseTool`
  that closes over it. Call the factory at agent construction time to bind the
  dependency without exposing it to the model as a parameter.

Usage::

    # Stateless — import directly
    from tools.ping_pong import ping_pong
    config.tools = [ping_pong]

    # Stateful — call the factory
    from tools.ping_pong import make_prefixed_ping_pong_tool
    config.tools = [make_prefixed_ping_pong_tool(prefix="[bot]")]
"""

from pydantic import BaseModel, Field

from ai_providers import BaseTool, define_tool


class _PingPongParams(BaseModel):
    value: str = Field(description="The value to echo back.")


# ---------------------------------------------------------------------------
# Stateless tool
# ---------------------------------------------------------------------------

@define_tool(description="Echoes back the provided value as a pong response.")
def ping_pong(params: _PingPongParams) -> str:
    """Return the value unchanged, wrapped in a 'pong' response."""

    return f"pong: {params.value}"


# ---------------------------------------------------------------------------
# Stateful tool factory
# ---------------------------------------------------------------------------

def make_prefixed_ping_pong_tool(prefix: str) -> BaseTool:
    """Return a ping-pong tool that prepends *prefix* to every response.

    This factory demonstrates the closure pattern for tools that depend on a
    runtime value owned by the caller (e.g. an agent or application context).
    The dependency is bound at construction time and is invisible to the model.

    Args:
        prefix: A string prepended to every pong response, e.g. ``"[bot]"``.

    Returns:
        A :class:`~ai_providers.BaseTool` whose handler closes over *prefix*.
    """

    @define_tool(description="Echoes back the provided value as a pong response.")
    def prefixed_ping_pong(params: _PingPongParams) -> str:
        return f"{prefix} pong: {params.value}"

    return prefixed_ping_pong
