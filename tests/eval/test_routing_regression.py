"""Routing regression eval — parametrized from evals/datasets/routing.jsonl.

Adding a JSONL line is sufficient to add a new routing regression test.
No Python changes needed.

Case fields:
  id                   — unique case identifier (shown in pytest output)
  user_message         — input text
  lang                 — detected/forced language
  expected_scenario    — exact scenario_id match (mutually exclusive with *_in / *_not)
  expected_scenario_in — list of acceptable scenario_ids (flexible match)
  expected_scenario_not — scenario_id that must NOT be returned (negative test)
  expected_risk_tier   — expected RiskTier int (0-2)
"""

import pytest

from evals.runner import load_dataset, run_routing_case

_CASES = load_dataset("routing")


def _case_id(case: dict) -> str:
    return f"{case['id']}: {case.get('note', '')}"


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_routing_regression(case: dict) -> None:
    result = run_routing_case(case)

    # Scenario assertion — three mutually exclusive assertion modes
    if "expected_scenario" in case:
        assert result["scenario_id"] == case["expected_scenario"], (
            f"[{case['id']}] expected scenario={case['expected_scenario']!r} "
            f"got {result['scenario_id']!r}"
        )
    elif "expected_scenario_in" in case:
        assert result["scenario_id"] in case["expected_scenario_in"], (
            f"[{case['id']}] expected scenario in {case['expected_scenario_in']} "
            f"got {result['scenario_id']!r}"
        )
    elif "expected_scenario_not" in case:
        assert result["scenario_id"] != case["expected_scenario_not"], (
            f"[{case['id']}] scenario must NOT be {case['expected_scenario_not']!r} "
            f"but got {result['scenario_id']!r}"
        )

    # Risk tier assertion
    assert result["risk_tier"] == case["expected_risk_tier"], (
        f"[{case['id']}] expected risk_tier={case['expected_risk_tier']} "
        f"got {result['risk_tier']}"
    )
