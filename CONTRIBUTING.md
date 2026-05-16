# Contributing

## Scope

This repository is a reusable template for AI provider integrations. Contributions should prioritize:

- Clear provider abstraction boundaries.
- Predictable async lifecycle management.
- Backward-compatible public API updates when possible.

## Local Setup

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Contribution Guidelines

- Keep provider-specific logic inside `ai_providers/<provider>.py`.
- Keep lifecycle orchestration in `ai_providers/factory.py`.
- Use `AsyncExitStack` for new dependency cleanup chains.
- Preserve type hints and docstring sections (Args/Returns/Raises).
- Avoid unrelated refactors in the same change.

## Pull Request Checklist

- Code runs locally.
- New provider branches are wired in create and dispose flows.
- Public exports are updated in `ai_providers/__init__.py` if needed.
- Dependencies are added or updated in `requirements.txt` when required.
- README is updated if architecture or usage changes.
