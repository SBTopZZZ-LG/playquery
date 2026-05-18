"""Shared helpers for tool builders."""

import dataclasses
import typing
from typing import Any

from pydantic import Field, create_model


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively inline all ``$ref``/``$defs`` in a JSON Schema."""
    defs: dict[str, Any] = schema.get("$defs", {})

    def _resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref: str = node["$ref"]
                if ref.startswith("#/$defs/"):
                    name = ref[len("#/$defs/") :]
                    if name in defs:
                        return _resolve(dict(defs[name]))
                return node
            return {k: _resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node

    result: dict[str, Any] = _resolve(schema)
    result.pop("$defs", None)
    return result


# Keys the Copilot API rejects or doesn't need.
_STRIP_KEYS: frozenset[str] = frozenset({"title", "uniqueItems", "additionalProperties"})


def _clean_node(node: Any) -> Any:
    if isinstance(node, list):
        return [_clean_node(item) for item in node]
    if not isinstance(node, dict):
        return node

    if "anyOf" in node:
        variants: list[Any] = node["anyOf"]
        null_v: dict[str, Any] = {"type": "null"}
        non_null = [v for v in variants if v != null_v]
        has_null = len(non_null) < len(variants)

        if has_null and len(non_null) == 1:
            # Nullable field with a single real type: unwrap null, merge outer keys in.
            inner: dict[str, Any] = {}
            for k, v in node.items():
                if k == "anyOf" or k in _STRIP_KEYS:
                    continue
                inner[k] = _clean_node(v)
            inner.update(_clean_node(non_null[0]))
            return inner

        # Multiple string variants (e.g. Enum | str [| None]): collapse to plain string.
        check = non_null if has_null else variants
        if all(isinstance(v, dict) and v.get("type") == "string" for v in check):
            outer: dict[str, Any] = {}
            for k, v in node.items():
                if k == "anyOf" or k in _STRIP_KEYS:
                    continue
                outer[k] = _clean_node(v)
            outer["type"] = "string"
            return outer

    return {k: _clean_node(v) for k, v in node.items() if k not in _STRIP_KEYS}


def sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten and sanitize a JSON Schema for the Copilot tool API.

    Applies :func:`inline_refs` first, then recursively:
    - Unwraps ``anyOf: [X, {"type": "null"}]`` to just ``X`` (nullable fields
      already have ``default: null`` so the null variant is redundant).
    - Collapses ``anyOf`` whose variants are all ``string``-typed (e.g.
      ``Enum | str``) to a plain ``{"type": "string"}``.
    - Strips ``title``, ``uniqueItems``, and ``additionalProperties`` which
      the Copilot API rejects or ignores.
    """
    return _clean_node(inline_refs(schema))


def make_params_model(model_name: str, primary_fields: dict, dc_type: type) -> type:
    """Build a Pydantic model combining *primary_fields* with all fields from *dc_type*.

    *primary_fields* is an ordered dict of ``{name: (annotation, FieldInfo)}``
    entries that are prepended before the dataclass-derived fields (e.g. query, url).

    # TODO (post-MVP): enrich dataclass fields with descriptions by reading
    # field-level metadata (e.g. dataclasses.field metadata dict or docstring
    # parsing) so the agent sees richer parameter documentation.
    """
    hints = typing.get_type_hints(dc_type)
    fields: dict = dict(primary_fields)

    for f in dataclasses.fields(dc_type):
        annotation = hints[f.name]
        if f.default is not dataclasses.MISSING:
            fields[f.name] = (annotation, Field(default=f.default))
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            fields[f.name] = (annotation, Field(default_factory=f.default_factory))  # type: ignore[misc]
        else:
            fields[f.name] = (annotation, Field(...))

    return create_model(model_name, **fields)
