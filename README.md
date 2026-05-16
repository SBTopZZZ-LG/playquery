# Python AI Providers Strategy Template

I built this template because I usually work on AI-enabled projects that need to switch between multiple providers, and I wanted a reusable foundation that avoids rebuilding the same provider wiring, lifecycle code, and agent orchestration in every new repository.

## Introduction

This project is an async-first Python template that applies a provider strategy + factory pattern to AI integrations.

Design goals:

- Decouple application code from provider-specific SDK logic.
- Standardize provider lifecycle operations (`initialize`, `send`, `dispose`).
- Centralize construction and resource management in one place.
- Make it straightforward to add new AI providers with minimal changes.
- Keep the `ai_providers` package fully self-contained — no concepts from the agent layer leak into it.
- Define agents as declarative contracts (identity only), so the caller retains full control over lifecycle and configuration.

## Requirements

- Python 3.10+
- Dependencies from `requirements.txt`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run demo:

```bash
python3 main.py
```

## Project Structure

```text
.
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── requirements.txt
├── pyrightconfig.json
├── main.py
├── ai_providers/
│   ├── __init__.py
│   ├── base.py
│   ├── copilot.py
│   ├── factory.py
│   └── tools.py
├── agents/
│   ├── __init__.py
│   ├── base.py
│   └── helpful_assistant.py
└── tools/
    ├── __init__.py
    └── ping_pong.py
```

Module responsibilities:

- `main.py`: Example entry point showing how to construct a config, select an agent, and run a provider session.
- `ai_providers/base.py`: Generic provider contract, base options, all tool-related types (`BaseTool`, `ToolHandler`, `ToolInvocation`, `ToolResult`), `JSONParseError`, and high-level query methods (`query`, `query_json`).
- `ai_providers/copilot.py`: Concrete provider implementation for the Copilot SDK.
- `ai_providers/factory.py`: `AIProviderConfig`, provider creation/disposal, and the `managed_ai_provider` context manager.
- `ai_providers/tools.py`: `define_tool` decorator — auto-generates JSON Schema from Pydantic models and wraps plain functions as `BaseTool` instances.
- `ai_providers/__init__.py`: Public exports for package consumers.
- `agents/base.py`: `BaseAgent` — an abstract base class declaring the two class-level attributes every agent must define: `system_prompt` and `tools`.
- `agents/helpful_assistant.py`: Example concrete agent. Defines its persona and tools; contains no lifecycle logic.
- `tools/`: Shared tool definitions reusable across multiple agents (stateless and stateful factory patterns).

## Provider + Factory Strategy

### Base Provider Contract

`BaseAIProvider` defines the lifecycle contract for all providers:

- `initialize_session()`
- `send_message_and_await_response(message: str) -> str`
- `dispose_session()`

Every provider must implement these async methods.

### Provider Options

Each concrete provider has a typed options dataclass inheriting from `BaseAIProviderOptions`.

Example (`CopilotProviderOptions`):

- `client`
- `model`
- `system_prompt`
- `timeout`

### Factory Responsibilities

`create_ai_provider(config)`:

- Accepts generic `AIProviderConfig`.
- Selects concrete provider by `ProviderType`.
- Starts provider dependencies (for Copilot: `CopilotClient.start()`).
- Returns a configured provider instance.

`dispose_ai_provider(provider)`:

- Disposes provider session and associated client resources.
- Raises typed errors on unsupported providers or cleanup failures.

`managed_ai_provider(config)`:

- Async context manager that creates the provider, calls `initialize_session()`, and disposes fully on exit.
- This is the primary entry point for running a provider session — callers use it directly.

### AsyncExitStack Lifecycle Design

Both the factory and `BaseAgent` use `contextlib.AsyncExitStack` for deterministic LIFO cleanup.

In the factory create path:

1. Start client.
2. Register rollback callback (`client.stop`) in the stack.
3. Build provider.
4. Call `stack.pop_all()` on success so rollback does not run.

In the factory dispose path:

1. Register `client.stop` callback (if available).
2. Register `provider.dispose_session` callback.
3. Stack unwinds in reverse order: session disposal → client stop.

## Agents

### Design Philosophy

The `agents` package and the `ai_providers` package are intentionally decoupled. Earlier iterations coupled them by having agents accept a config, inject their `system_prompt` and `tools` into it, and manage the provider lifecycle internally. That approach created two problems:

- The `ai_providers` package needed concepts (like a "backend-only" config) that only existed to serve the agent pattern.
- Callers had no control over the provider lifecycle — it was hidden inside the agent.

The current design separates responsibilities cleanly:

- **`ai_providers`** owns everything about talking to a backend: construction, lifecycle, and querying. It has no knowledge of agents.
- **`agents`** owns identity only: what persona to use and what tools to expose.

### What `BaseAgent` Is

`BaseAgent` is an abstract base class — a contract, not an implementation. It declares two class-level attributes that every concrete agent must define:

```python
class BaseAgent(ABC):
    system_prompt: str
    tools: list[BaseTool]
```

There is no constructor, no lifecycle logic, and no provider reference. Inheriting from `ABC` makes direct instantiation of `BaseAgent` a `TypeError`, which ensures subclasses always declare both attributes.

### Defining an Agent

A concrete agent is a class with two attributes:

```python
class HelpfulAssistantAgent(BaseAgent):
    system_prompt: str = "You are a helpful assistant."
    tools: list[BaseTool] = [ping_pong]
```

Nothing else. The agent carries no state and manages no resources.

### How the Caller Uses an Agent

The caller constructs the `AIProviderConfig`, drawing `system_prompt` and `tools` from the chosen agent class:

```python
config = AIProviderConfig(
    provider_type=ProviderType.COPILOT,
    model="gpt-4.1",
    timeout=120,
    system_prompt=HelpfulAssistantAgent.system_prompt,
    tools=HelpfulAssistantAgent.tools,
)

async with managed_ai_provider(config) as provider:
    response = await provider.query("Hello")
    print(response)
```

This means:

- Swapping agents is a single-line change (`HelpfulAssistantAgent` → `AnotherAgent`).
- Lifecycle control stays entirely with the caller.
- The `ai_providers` package remains fully agnostic of the agents package.

### Query Interface

`query` and `query_json` are methods on `BaseAIProvider`, not on agents. They are available on any provider instance yielded by `managed_ai_provider`:

- `provider.query(message: str) -> str` — send a message, return the raw response string.
- `provider.query_json(message: str, max_retries: int = 3) -> dict` — send a message, parse the response as JSON. On parse failure, automatically sends the error back to the model and retries up to `max_retries` times before raising `JSONParseError`.

## Tools

### Defining Tools with `@define_tool`

`define_tool` turns a plain function into a `BaseTool`. When the first parameter is typed as a Pydantic model, the JSON Schema is generated automatically:

```python
from pydantic import BaseModel, Field
from ai_providers import define_tool

class SearchParams(BaseModel):
    query: str = Field(description="The search query")

@define_tool(description="Search the web for a query")
def search_web(params: SearchParams) -> str:
    return do_search(params.query)
```

The decorated name becomes a `BaseTool` instance — assign it to `config.tools` directly.

`define_tool` can also be used as a plain function call when the handler is defined elsewhere:

```python
tool = define_tool("search_web", description="Search the web", handler=my_handler)
```

### Supported Handler Signatures

| Signature | Behaviour |
| --- | --- |
| `fn()` | Called with no arguments |
| `fn(invocation: ToolInvocation)` | Receives the raw invocation dict |
| `fn(params: PydanticModel)` | Parameters validated and unpacked via Pydantic |
| `fn(params: PydanticModel, invocation: ToolInvocation)` | Params + raw invocation |

Return values are normalised automatically: `str` → success result, `None` → empty success, `dict` → passed through, Pydantic model → JSON-serialised.

### Where to Define Tools

#### Agent-specific tools

Tools that belong to one agent should be defined at module level in the same file as the agent:

```python
# agents/my_agent.py
from pydantic import BaseModel, Field
from ai_providers import BaseTool, define_tool
from .base import BaseAgent

class _SummaryParams(BaseModel):
    text: str = Field(description="Text to summarise")

@define_tool(description="Summarise a block of text")
def _summarise(params: _SummaryParams) -> str:
    return summarise(params.text)

class MyAgent(BaseAgent):
    system_prompt: str = "You are a summarisation assistant."
    tools: list[BaseTool] = [_summarise]
```

#### Shared tools (`tools/` package)

Tools used by more than one agent live in the `tools/` package. Two patterns are supported:

**Stateless** — pure functions with no external dependencies. Define with `@define_tool` and import directly:

```python
# tools/search.py
@define_tool(description="Search the web")
def search_web(params: SearchParams) -> str:
    ...

# agents/my_agent.py
from tools.search import search_web
config.tools = [search_web]
```

**Stateful factory** — tools that close over a runtime dependency (e.g. a database connection or API client). Define a factory function that accepts the dependency and returns a `BaseTool`. The dependency is bound at agent construction time and is invisible to the model:

```python
# tools/database.py
def make_query_tool(db_url: str) -> BaseTool:
    @define_tool(description="Run a read-only database query")
    def query_db(params: QueryParams) -> str:
        return run_query(db_url, params.sql)  # db_url closed over
    return query_db
```

```python
# main.py (or wherever the session is set up)
from tools.database import make_query_tool
from agents import MyAgent

config = AIProviderConfig(
    provider_type=ProviderType.COPILOT,
    model="gpt-4.1",
    timeout=120,
    system_prompt=MyAgent.system_prompt,
    tools=[*MyAgent.tools, make_query_tool(db_url)],
)
```

The rule of thumb: if the dependency can be represented as data in the tool's arguments, keep it module-level. If it is a runtime resource that the agent lifecycle manages, bind it at construction time via a factory.

## Adding a New Agent

### 1. Create an agent module

Add a new file under `agents/` inheriting from `BaseAgent`:

- Define `system_prompt` as a class-level string attribute.
- Define `tools` as a class-level list of `BaseTool` instances.
- Define any agent-specific tools at module level in the same file.

```python
# agents/my_agent.py
from ai_providers import BaseTool
from .base import BaseAgent

class MyAgent(BaseAgent):
    system_prompt: str = "You are a specialist assistant."
    tools: list[BaseTool] = []
```

### 2. Export the agent

Update `agents/__init__.py` exports.

### 3. Use the agent

In your entry point, pass the agent's attributes into `AIProviderConfig`:

```python
config = AIProviderConfig(
    provider_type=ProviderType.COPILOT,
    model="gpt-4.1",
    timeout=120,
    system_prompt=MyAgent.system_prompt,
    tools=MyAgent.tools,
)

async with managed_ai_provider(config) as provider:
    response = await provider.query("Hello")
```

### 4. Add shared tools (optional)

If a tool is needed by multiple agents, add it to the `tools/` package following the stateless or stateful factory patterns described above.

---

## Adding a New Provider

### 1. Create a provider module

Add a new file under `ai_providers/` (for example `openai_provider.py`) with:

- An options dataclass inheriting `BaseAIProviderOptions`.
- A provider class inheriting `BaseAIProvider[YourOptions]`.
- Implementations for all lifecycle methods.

### 2. Add enum value

Update `ProviderType` in `ai_providers/factory.py`.

### 3. Extend factory create/dispose

In `create_ai_provider(config)`:

- Add a branch for the new provider.
- Start SDK/client resources.
- Register rollback callbacks with `AsyncExitStack`.
- Construct provider and return after `stack.pop_all()`.

In `dispose_ai_provider(provider)`:

- Add type-specific cleanup registration.
- Keep cleanup operations stack-managed and async-safe.

### 4. Export the new provider

Update `ai_providers/__init__.py` exports.

### 5. Add dependency

Update `requirements.txt` if the provider requires an SDK.

## Error Handling Notes

- Invalid or unsupported providers raise `ValueError`.
- Startup/initialization/cleanup runtime failures raise `RuntimeError`.
- Concrete providers should validate required options early.

## Extension Guidelines

- Keep provider-specific SDK code inside provider modules, not app code.
- Keep `main.py` orchestration-oriented and provider-agnostic.
- Prefer `managed_ai_provider` in app code for automatic lifecycle handling.
- Keep options strongly typed to simplify validation and refactoring.

## Current Dependency

| Provider | Package | Version Constraint | Notes |
| --- | --- | --- | --- |
| Copilot | github-copilot-sdk | >=0.1.25,<0.2.0 | Active provider in this template |

Planned providers can be added as new rows as they are implemented.

## TODO

- [x] Use AsyncExitStack to manage resource life-cycle and maintain clean code
- [x] Add `agents` package with `BaseAgent` (AsyncExitStack lifecycle, `query`, `query_json`) and `HelpfulAssistantAgent` example
- [x] Add `define_tool` decorator with Pydantic schema auto-generation
- [x] Add `tools/` package for shared tools with stateless and stateful factory patterns
- ~~[ ] Add agent factory / registry (similar to `ai_providers/factory.py`) under `agents/factory.py`~~
- [ ] Unit/Integration tests for `ai_providers`, `agents`, and `tools` packages
- [ ] Add Claude AI provider
- [ ] Add OpenAI provider

## License

See `LICENSE`.
