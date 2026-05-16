"""Output safety regression eval — parametrized from evals/datasets/output_safety.jsonl.

Verifies that the deterministic output validator correctly allows or blocks
LLM responses before they reach the user.

Case fields:
  id               — unique case identifier
  response         — LLM response text to validate
  expected_safe    — bool: True if response should pass, False if it should be blocked
  expected_reason  — str | null: expected block_reason when expected_safe is False
"""

import pytest

from evals.runner import load_dataset, run_output_safety_case

_CASES = load_dataset("output_safety")


def _case_id(case: dict) -> str:
    return f"{case['id']}: {case.get('note', '')}"


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_output_safety_regression(case: dict) -> None:
    result = run_output_safety_case(case)

    assert result["is_safe"] == case["expected_safe"], (
        f"[{case['id']}] expected is_safe={case['expected_safe']} "
        f"got is_safe={result['is_safe']} block_reason={result['block_reason']!r}"
    )

    if not case["expected_safe"] and case.get("expected_reason"):
        assert result["block_reason"] == case["expected_reason"], (
            f"[{case['id']}] expected block_reason={case['expected_reason']!r} "
            f"got {result['block_reason']!r}"
        )
