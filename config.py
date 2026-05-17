"""Root Pydantic config model and JSON Schema generation for PlayQuery."""

from __future__ import annotations

import json
import sys

from pydantic import BaseModel

from scraper.config import ScraperConfig
from search_engine.config import SearchEngineConfig


class PlayQueryConfig(BaseModel):
    """Root configuration model for playquery.yaml."""

    search_engine: SearchEngineConfig
    scraper: ScraperConfig | None = None


if __name__ == "__main__":
    json.dump(PlayQueryConfig.model_json_schema(), sys.stdout, indent=2)
    sys.stdout.write("\n")
