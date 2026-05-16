"""Tests for SafetyClassifier unit behavior — S-3, S-4."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import RiskLevel
from app.safety.safety_classifier import SafetyClassifier


def _make_client(content: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value=resp)
    return client


_VALID_SAFE = (
    '{"risk_level": 0, "risk_type": "none", "confidence": 1.0, '
    '"reason": "ok", "requires_crisis_response": false, "requires_professional_referral": false}'
)


@pytest.mark.asyncio
async def test_json_parse_error_returns_elevated_distress_fallback() -> None:
    """S-3: malformed classifier JSON → safe non-crisis fallback (risk_level=ELEVATED_DISTRESS=2)."""
    client = _make_client("not valid json {{{")
    classifier = SafetyClassifier(client)
    result = await classifier.classify("Мне немного грустно")
    assert result.risk_level == RiskLevel.ELEVATED_DISTRESS
    assert result.requires_crisis_response is False
    assert result.requires_professional_referral is True


@pytest.mark.asyncio
async def test_model_passed_to_chat_completion() -> None:
    """S-4a: SafetyClassifier passes its model= to client.chat_completion."""
    client = _make_client(_VALID_SAFE)
    classifier = SafetyClassifier(client, model="test/model-1b")
    await classifier.classify("Привет")
    call_kwargs = client.chat_completion.call_args.kwargs
    assert call_kwargs.get("model") == "test/model-1b"


@pytest.mark.asyncio
async def test_none_model_passes_none_to_chat_completion() -> None:
    """S-4b: SafetyClassifier with model=None passes None to chat_completion (client uses default)."""
    client = _make_client(_VALID_SAFE)
    classifier = SafetyClassifier(client, model=None)
    await classifier.classify("Привет")
    call_kwargs = client.chat_completion.call_args.kwargs
    assert call_kwargs.get("model") is None
