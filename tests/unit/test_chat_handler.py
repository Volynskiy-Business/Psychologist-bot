"""Tests for the main chat message handler.

Focus: the regression where the normal-flow LLM call sent
``settings.default_model`` as the system message content instead of the
real ``SYSTEM_PROMPT``. These tests pin the correct behavior with mocks
only — no real network, Telegram, or OpenRouter calls.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openrouter_client import OpenRouterResponse
from app.ai.prompts.system_prompt import SYSTEM_PROMPT
from app.bot.handlers import chat as chat_module
from app.db.models import RiskLevel


def _make_message(text: str = "Привет, мне немного грустно сегодня") -> SimpleNamespace:
    """Build a minimal aiogram-message stand-in.

    Only the attributes accessed by ``handle_message`` are populated.
    ``answer`` and ``chat.do_action`` are AsyncMocks so we can assert calls.
    """
    user = SimpleNamespace(language_code="ru", id=1, is_bot=False)
    chat = SimpleNamespace(do_action=AsyncMock())
    return SimpleNamespace(
        text=text,
        from_user=user,
        chat=chat,
        answer=AsyncMock(),
    )


def _fake_client(response_text: str = "Я тебя слышу.") -> AsyncMock:
    """Build a fake OpenRouterClient instance for patching the constructor."""
    client = AsyncMock()
    client.chat_completion = AsyncMock(
        return_value=OpenRouterResponse(
            content=response_text,
            model="test-model",
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=42,
        )
    )
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_normal_flow_sends_system_prompt() -> None:
    """The system message in the normal flow must be the real SYSTEM_PROMPT,
    not the model id or any other placeholder. This pins the fix for the bug
    where ``settings.default_model`` was passed as the system content."""
    message = _make_message("сегодня было тяжело на работе")
    fake_client = _fake_client()

    # Safety classifier must not flag this benign message; patch to NO_RISK.
    safe_classification = SimpleNamespace(risk_level=RiskLevel.NO_RISK)

    with patch.object(chat_module, "OpenRouterClient", return_value=fake_client), \
         patch.object(chat_module, "SafetyClassifier") as classifier_cls:
        classifier_cls.return_value.classify = AsyncMock(return_value=safe_classification)
        await chat_module.handle_message(message)

    fake_client.chat_completion.assert_awaited_once()
    kwargs = fake_client.chat_completion.await_args.kwargs
    messages = kwargs["messages"]

    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    # Negative regression guard: never send the model id as system content.
    assert messages[0]["content"] != "openrouter/free"
    assert "openrouter/" not in messages[0]["content"].splitlines()[0]

    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "сегодня было тяжело на работе"

    # The bot reply must be delivered via Telegram.
    message.answer.assert_awaited()
    fake_client.close.assert_awaited()


@pytest.mark.asyncio
async def test_imminent_risk_skips_llm_call() -> None:
    """Deterministic Level-4 phrases must short-circuit to a crisis response
    and never reach the LLM. Defense in depth for safety."""
    message = _make_message("я хочу умереть")
    fake_client = _fake_client()

    with patch.object(chat_module, "OpenRouterClient", return_value=fake_client):
        await chat_module.handle_message(message)

    fake_client.chat_completion.assert_not_called()
    message.answer.assert_awaited_once()
    sent_text = message.answer.await_args.args[0]
    assert sent_text  # non-empty crisis response


@pytest.mark.asyncio
async def test_classifier_flagged_crisis_skips_llm_call() -> None:
    """If the LLM safety classifier returns POSSIBLE_CRISIS or higher, we
    must NOT continue to the normal LLM flow."""
    message = _make_message("мне всё равно что будет дальше")
    fake_client = _fake_client()

    flagged = SimpleNamespace(risk_level=RiskLevel.POSSIBLE_CRISIS)

    with patch.object(chat_module, "OpenRouterClient", return_value=fake_client), \
         patch.object(chat_module, "SafetyClassifier") as classifier_cls:
        classifier_cls.return_value.classify = AsyncMock(return_value=flagged)
        await chat_module.handle_message(message)

    fake_client.chat_completion.assert_not_called()
    message.answer.assert_awaited_once()
    sent_text = message.answer.await_args.args[0]
    assert sent_text  # non-empty crisis response
    fake_client.close.assert_awaited()


@pytest.mark.asyncio
async def test_classifier_failure_continues_with_system_prompt() -> None:
    """If the safety classifier raises, the handler must still send the real
    SYSTEM_PROMPT (cautious normal flow), not crash and not regress to the
    old bug."""
    message = _make_message("устал и плохо сплю")
    fake_client = _fake_client()

    with patch.object(chat_module, "OpenRouterClient", return_value=fake_client), \
         patch.object(chat_module, "SafetyClassifier") as classifier_cls:
        classifier_cls.return_value.classify = AsyncMock(side_effect=RuntimeError("boom"))
        await chat_module.handle_message(message)

    fake_client.chat_completion.assert_awaited_once()
    messages = fake_client.chat_completion.await_args.kwargs["messages"]
    assert messages[0]["content"] == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_empty_message_is_ignored() -> None:
    """Messages with no text (photos, stickers, etc.) must be ignored."""
    user = SimpleNamespace(language_code="ru", id=1, is_bot=False)
    chat = SimpleNamespace(do_action=AsyncMock())
    message = SimpleNamespace(text=None, from_user=user, chat=chat, answer=AsyncMock())

    fake_client = _fake_client()
    with patch.object(chat_module, "OpenRouterClient", return_value=fake_client):
        await chat_module.handle_message(message)

    fake_client.chat_completion.assert_not_called()
    message.answer.assert_not_called()
