"""Tests for output validation — V-1 to V-6."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.output_validation import validate_support_response


# ── V-1: clean supportive text passes ─────────────────────────────────────────

def test_clean_response_passes() -> None:
    """V-1: a normal supportive response is not blocked."""
    text = "It sounds like you're going through a really tough time. Let's try a breathing exercise together."
    safe, reason = validate_support_response(text)
    assert safe is True
    assert reason is None


# ── V-2: identity claim blocks ────────────────────────────────────────────────

def test_identity_claim_blocked() -> None:
    """V-2: 'I am your doctor' is blocked."""
    safe, reason = validate_support_response("I am your doctor and I recommend this treatment.")
    assert safe is False
    assert reason == "identity_claim"


def test_as_your_therapist_blocked() -> None:
    """V-2b: 'as your therapist' is blocked."""
    safe, reason = validate_support_response("As your therapist, I think you should do this.")
    assert safe is False
    assert reason == "identity_claim"


def test_russian_psychologist_self_claim_blocked() -> None:
    """V-2c: Russian bot self-description as a psychologist is blocked."""
    safe, reason = validate_support_response("Привет! Меня зовут Мария, я психолог.")
    assert safe is False
    assert reason == "identity_claim"


# ── V-3: diagnosis language blocks ────────────────────────────────────────────

def test_diagnosis_blocked() -> None:
    """V-3: asserting the user has a disorder is blocked."""
    safe, reason = validate_support_response("Based on what you said, you have major depressive disorder.")
    assert safe is False
    assert reason == "diagnosis"


# ── V-4: medication instruction blocks ───────────────────────────────────────

def test_stop_medication_blocked() -> None:
    """V-4: telling the user to stop medication is blocked."""
    safe, reason = validate_support_response("You should stop taking your antidepressants immediately.")
    assert safe is False
    assert reason == "medication_instruction"


def test_prescribe_blocked() -> None:
    """V-4b: claiming to prescribe is blocked."""
    safe, reason = validate_support_response("I can prescribe something that will help you.")
    assert safe is False
    assert reason == "prescribing_claim"


# ── V-5: treatment claim blocks ──────────────────────────────────────────────

def test_can_cure_blocked() -> None:
    """V-5: claiming to cure is blocked."""
    safe, reason = validate_support_response("I can cure your anxiety with this technique.")
    assert safe is False
    assert reason == "treatment_claim"


# ── V-6: blocked response triggers output_blocked message in chat handler ─────

@pytest.mark.asyncio
async def test_chat_handler_sends_output_blocked_message() -> None:
    """V-6: when validate_support_response returns False, chat handler sends output_blocked text."""
    from app.bot.handlers.chat import handle_message

    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = 55000
    msg = MagicMock()
    msg.text = "Tell me about myself"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    fake_response = MagicMock()
    fake_response.content = "I am your doctor and you have depression disorder."

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    mock_classification = MagicMock()
    from app.db.models import RiskLevel
    mock_classification.risk_level = RiskLevel.NO_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
            patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
            patch("app.bot.handlers.chat.get_user_by_telegram_id", new_callable=AsyncMock, return_value=None),
            patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
            patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
        ):
        await handle_message(msg)

    msg.answer.assert_called_once()
    sent_text = msg.answer.call_args.args[0]
    # Must send the output_blocked fallback, not the blocked LLM content
    assert "I am your doctor" not in sent_text
    assert "can't send" in sent_text.lower() or "cannot" in sent_text.lower() or "не могу" in sent_text.lower()
