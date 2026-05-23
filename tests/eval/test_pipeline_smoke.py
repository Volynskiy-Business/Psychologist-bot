"""Pipeline smoke eval — verifies full SupportPipeline end-to-end without real LLM.

Uses a mocked OpenRouterClient that returns a predetermined safe response,
so this test exercises every deterministic stage of the pipeline:
  intake → scenario selection → prompt build → (mocked) LLM → quality check →
  output validation → PipelineResult

Adding cases to _SMOKE_CASES exercises additional routing + prompt paths
at zero LLM cost.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.orchestration.models import RiskTier
from app.ai.orchestration.pipeline import SupportPipeline

_SAFE_RESPONSE = (
    "I hear you. That sounds really difficult. "
    "What's been weighing on you the most right now?"
)

_SMOKE_CASES = [
    {
        "id": "P01",
        "user_text": "Я очень устал и не могу справиться.",
        "lang": "ru",
        "expected_scenario": "exhaustion",
        "expected_risk_tier": RiskTier.TIER_1,
        "expected_is_safe": True,
    },
    {
        "id": "P02",
        "user_text": "She cheated on me after 10 years.",
        "lang": "en",
        "expected_scenario": "breakup_divorce",
        "expected_risk_tier": RiskTier.TIER_1,
        "expected_is_safe": True,
    },
    {
        "id": "P03",
        "user_text": "I got scammed and lost all my savings.",
        "lang": "en",
        "expected_scenario": "financial_fraud_trauma",
        "expected_risk_tier": RiskTier.TIER_1,
        "expected_is_safe": True,
    },
    {
        "id": "P04",
        "user_text": "Hello, I just need someone to talk to.",
        "lang": "en",
        "expected_scenario": "general_support",
        "expected_risk_tier": RiskTier.TIER_0,
        "expected_is_safe": True,
    },
]


def _make_mock_client(response_text: str) -> Any:
    mock_response = MagicMock()
    mock_response.content = response_text
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value=mock_response)
    return client


def _case_id(case: dict) -> str:
    return f"{case['id']}: {case['user_text'][:40]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _SMOKE_CASES, ids=[_case_id(c) for c in _SMOKE_CASES])
async def test_pipeline_smoke(case: dict) -> None:
    client = _make_mock_client(_SAFE_RESPONSE)
    pipeline = SupportPipeline(client, model="smoke-model")

    result = await pipeline.run(case["user_text"], case["lang"], history=[])

    assert result.scenario_id == case["expected_scenario"], (
        f"[{case['id']}] expected scenario={case['expected_scenario']!r} "
        f"got {result.scenario_id!r}"
    )
    assert result.risk_tier == case["expected_risk_tier"], (
        f"[{case['id']}] expected risk_tier={case['expected_risk_tier']} "
        f"got {result.risk_tier}"
    )
    assert result.is_safe == case["expected_is_safe"], (
        f"[{case['id']}] expected is_safe={case['expected_is_safe']} "
        f"got {result.is_safe}, block_reason={result.block_reason}"
    )
    assert result.intake_language == case["lang"]
    assert result.content == _SAFE_RESPONSE
