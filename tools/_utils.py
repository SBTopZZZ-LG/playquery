"""Shared helpers for tool builders."""

import dataclasses
import typing

from pydantic import Field, create_model


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
