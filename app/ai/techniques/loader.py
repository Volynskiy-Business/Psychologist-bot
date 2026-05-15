"""Technique library loader — reads library.yaml and exposes typed accessors."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from app.ai.orchestration.models import ScenarioData, TechniqueData

_LIBRARY_PATH = Path(__file__).parent / "library.yaml"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(_LIBRARY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_all_techniques() -> list[TechniqueData]:
    raw = _load_raw()
    return [TechniqueData(**t) for t in raw["techniques"]]


def get_technique(technique_id: str) -> Optional[TechniqueData]:
    return next((t for t in get_all_techniques() if t.id == technique_id), None)


def select_technique(
    scenario: Optional[ScenarioData],
    risk_tier: int,
) -> Optional[TechniqueData]:
    """Return the first recommended technique that is safe for the current risk tier."""
    if scenario is None or not scenario.recommended_techniques:
        return None
    technique_map = {t.id: t for t in get_all_techniques()}
    for tid in scenario.recommended_techniques:
        technique = technique_map.get(tid)
        if technique and technique.risk_ceiling >= risk_tier:
            return technique
    return None
