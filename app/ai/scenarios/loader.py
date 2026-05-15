"""Scenario library loader — reads library.yaml and exposes typed accessors."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from app.ai.orchestration.models import ScenarioData

_LIBRARY_PATH = Path(__file__).parent / "library.yaml"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(_LIBRARY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_all_scenarios() -> list[ScenarioData]:
    raw = _load_raw()
    return [ScenarioData(**s) for s in raw["scenarios"]]


def get_scenario(scenario_id: str) -> Optional[ScenarioData]:
    return next((s for s in get_all_scenarios() if s.id == scenario_id), None)
