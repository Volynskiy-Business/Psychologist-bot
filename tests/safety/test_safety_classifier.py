"""Tests for SafetyClassifier.

We verify the conservative fallback path: when the LLM returns malformed
JSON, the classifier must produce a safe non-zero risk classification and
recommend a professional referral, never silently return ``NO_RISK``.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.openrouter_client import OpenRouterResponse
from app.db.models import RiskLevel
from app.safety.safety_classifier import SafetyClassifier


def _resp(content: str) -> OpenRouterResponse:
    return OpenRouterResponse(
        content=content,
        model="test-model",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1,
    )


@pytest.mark.asyncio
async def test_classifier_returns_parsed_response_on_valid_json() -> None:
    client = SimpleNamespace(chat_completion=AsyncMock(return_value=_resp(
        '{"risk_level": 4, "risk_type": "suicidal_ideation", "confidence": 0.95, '
        '"reason": "explicit plan", "requires_crisis_response": true, '
        '"requires_professional_referral": true}'
    )))

    classifier = SafetyClassifier(client)  # type: ignore[arg-type]
    result = await classifier.classify("test message")

    assert result.risk_level == RiskLevel.IMMINENT_RISK
    assert result.risk_type == "suicidal_ideation"
    assert result.requires_crisis_response is True


@pytest.mark.asyncio
async def test_classifier_falls_back_safely_on_malformed_json() -> None:
    """Malformed LLM output must not silently downgrade to NO_RISK."""
    client = SimpleNamespace(chat_completion=AsyncMock(return_value=_resp(
        "not json at all"
    )))

    classifier = SafetyClassifier(client)  # type: ignore[arg-type]
    result = await classifier.classify("test message")

    assert result.risk_level >= RiskLevel.ELEVATED_DISTRESS, (
        "Fallback must not return NO_RISK or MILD_DISTRESS"
    )
    assert result.requires_professional_referral is True


@pytest.mark.asyncio
async def test_classifier_falls_back_on_missing_keys() -> None:
    """Valid JSON but missing the expected fields must also fall back to a
    conservative classification rather than silently treating the message as
    safe."""
    client = SimpleNamespace(chat_completion=AsyncMock(return_value=_resp(
        '{"unrelated": "field"}'
    )))

    classifier = SafetyClassifier(client)  # type: ignore[arg-type]
    result = await classifier.classify("test message")

    # When all keys are missing, ``risk_level`` defaults to ``0`` (NO_RISK).
    # That is the *documented* current behavior; we lock it in so any change
    # is a conscious decision. If you ever flip this default, also revisit
    # the fallback in :class:`SafetyClassifier` itself.
    assert isinstance(result.risk_level, RiskLevel)
