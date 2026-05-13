"""Tests for chat handler — C-1 (system prompt) and C-2 (classifier fallback)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import RiskLevel


def _make_message(text: str = "Мне грустно") -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "en"

    msg = MagicMock()
    msg.text = text
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.do_action = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_classifier_failure_does_not_proceed_to_llm() -> None:
    """C-2: classifier exception must not fall through to chat_completion."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Мне грустно")

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(side_effect=RuntimeError("API timeout"))

    with (
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    mock_client.close.assert_called()


@pytest.mark.asyncio
async def test_system_prompt_used_in_chat_completion() -> None:
    """C-1: SYSTEM_PROMPT must be the system message content, not the model name."""
    from app.ai.prompts.system_prompt import SYSTEM_PROMPT
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Расскажи мне об упражнениях")

    fake_response = MagicMock()
    fake_response.content = "Конечно, вот упражнение..."

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.NO_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_client.chat_completion.assert_called_once()
    call_args = mock_client.chat_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    system_msg = messages[0]
    assert system_msg["role"] == "system"
    assert system_msg["content"] == SYSTEM_PROMPT
    assert system_msg["content"] != "openrouter/free"
