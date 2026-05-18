"""PlayQuery — main entry point."""

import asyncio
import itertools
import sys
from typing import Any

from agents import PlayQueryAgent
from ai_providers import (
    AIProviderConfig,
    BaseTool,
    ProviderType,
    ToolInvocation,
    ToolResult,
    managed_ai_provider,
)
from core import PlayQueryService
from scraper import load_scraper
from search_engine import load_engine

_BRAILLE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def _read_query() -> str:
    """Read lines from stdin until EOF (Ctrl+D) and return the joined text."""
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line:  # EOF
            break
        lines.append(line)
    return "".join(lines).strip()


async def _spinner() -> None:
    """Animate a braille spinner on the current line until cancelled."""
    for frame in itertools.cycle(_BRAILLE):
        sys.stdout.write(f"\rPlayQuery > {frame} ")
        sys.stdout.flush()
        try:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            return


def _fmt_args(args: Any) -> str:
    """Format tool arguments as a compact key=value string."""
    if not isinstance(args, dict):
        return repr(args)
    parts = []
    for k, v in args.items():
        s = repr(v)
        if len(s) > 60:
            s = s[:57] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def _with_logging(tool: BaseTool) -> BaseTool:
    """Wrap a tool's handler to print a status line on each invocation."""
    original = tool.handler

    async def _logged(invocation: ToolInvocation) -> ToolResult:
        sys.stdout.write(
            f"\r\033[K  → {invocation['tool_name']}({_fmt_args(invocation['arguments'])})\n"
        )
        sys.stdout.flush()
        result = original(invocation)
        if asyncio.iscoroutine(result):
            result = await result
        return result  # type: ignore[return-value]

    tool.handler = _logged
    return tool


async def main() -> None:
    """Start the PlayQuery agent and run an interactive query loop."""

    engine = load_engine()
    scraper = load_scraper()
    service = PlayQueryService(engine=engine, scraper=scraper)
    agent = PlayQueryAgent(service)

    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="claude-sonnet-4.6",
        timeout=300,
        system_prompt=agent.system_prompt,
        tools=[_with_logging(t) for t in agent.tools],
    )

    try:
        async with managed_ai_provider(config) as provider:
            print("PlayQuery ready. Type your query and press Ctrl+D to submit (Ctrl+C to exit).\n")
            while True:
                sys.stdout.write("> ")
                sys.stdout.flush()

                query = await asyncio.to_thread(_read_query)
                if not query:
                    print()  # blank line so the next prompt isn't flush against the last
                    continue

                spinner_task = asyncio.create_task(_spinner())
                try:
                    response = await provider.query(query)
                finally:
                    spinner_task.cancel()
                    await asyncio.gather(spinner_task, return_exceptions=True)

                print(f"\n{response}\n")

    except KeyboardInterrupt:
        print("\nBye!")
    except (ValueError, RuntimeError, OSError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
