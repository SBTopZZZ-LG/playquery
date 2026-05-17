"""Pydantic config models and JSON Schema generation for PlayQuery."""

from __future__ import annotations

import json
import sys
from typing import Annotated

from pydantic import BaseModel, Field

from .searxng import SearXNGOptions

# Extend this union as new engine implementations are added:
#   SearchEngineConfig = Annotated[
#       Union[SearXNGOptions, SerperOptions, ...],
#       Field(discriminator="type"),
#   ]
SearchEngineConfig = Annotated[
    SearXNGOptions,
    Field(discriminator="type"),
]


class PlayQueryConfig(BaseModel):
    """Root configuration model for playquery.yaml."""

    search_engine: SearchEngineConfig


if __name__ == "__main__":
    json.dump(PlayQueryConfig.model_json_schema(), sys.stdout, indent=2)
    sys.stdout.write("\n")
