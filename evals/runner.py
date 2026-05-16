"""Eval runner: deterministic contract functions for regression evaluation.

Each function wraps a real application component (no mocks, no LLM calls)
and returns a plain dict that eval tests can assert against.

Adding a new scenario to a dataset JSONL is sufficient to add a regression test;
no Python changes are needed.
"""

import json
from pathlib import Path
from typing import Any

_DATASETS_DIR = Path(__file__).parent / "datasets"


def load_dataset(name: str) -> list[dict[str, Any]]:
    """Load a JSONL dataset by base name (without extension)."""
    path = _DATASETS_DIR / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_routing_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single routing eval case.  No LLM calls.

    Input keys: user_message, lang
    Output keys: scenario_id, risk_tier (int), detected_emotion, intensity
    """
    from app.ai.routing.intake import classify_intake

    result = classify_intake(case["user_message"], case.get("lang", ""))
    return {
        "scenario_id": result.scenario_id,
        "risk_tier": int(result.risk_tier),
        "detected_emotion": result.detected_emotion,
        "intensity": result.intensity,
    }


def run_output_safety_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single output safety eval case.  No LLM calls.

    Input keys: response
    Output keys: is_safe (bool), block_reason (str | None)
    """
    from app.ai.output_validation import validate_support_response

    is_safe, block_reason = validate_support_response(case["response"])
    return {"is_safe": is_safe, "block_reason": block_reason}
