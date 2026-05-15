"""Tests for chat handler — C-1 (system prompt), C-2 (classifier fallback), C-3 (consent gate), C-12/13 (rate limit)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.db.models import RiskLevel


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(str(status_code), request=request, response=response)


def _make_message(text: str = "Мне грустно", user_id: int = 12345) -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

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
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
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
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
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


@pytest.mark.asyncio
async def test_no_consent_blocks_classifier_and_llm() -> None:
    """C-3: user without consent must not reach classifier or LLM."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Мне грустно", user_id=99001)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_classifier.classify.assert_not_called()
    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_no_consent_reply_contains_consent_button() -> None:
    """C-3: the consent prompt reply must include the consent_agree keyboard button."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Привет", user_id=99002)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.OpenRouterClient"),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once()
    call_kwargs = msg.answer.call_args.kwargs
    keyboard = call_kwargs.get("reply_markup")
    assert keyboard is not None
    buttons = [btn for row in keyboard.inline_keyboard for btn in row]
    assert any(btn.callback_data == "consent_agree" for btn in buttons)


@pytest.mark.asyncio
async def test_consent_allows_chat_path() -> None:
    """C-3: user with consent proceeds to the normal support flow."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Расскажи как дышать", user_id=99003)

    fake_response = MagicMock()
    fake_response.content = "Вот упражнение на дыхание..."

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.NO_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_crisis_check_runs_before_consent_gate() -> None:
    """C-7: deterministic crisis check fires before consent gate — crisis text answered without consent."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("я хочу умереть", user_id=77777)

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock()

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once()
    mock_classifier.classify.assert_not_called()
    mock_client.chat_completion.assert_not_called()


@pytest.mark.asyncio
async def test_crisis_records_safety_event() -> None:
    """C-8: crisis detection writes a SafetyEvent with correct telegram_user_id."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("я хочу умереть", user_id=55555)
    mock_record = AsyncMock()

    with (
        patch("app.bot.handlers.chat.record_safety_event", mock_record),
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
    ):
        await handle_message(msg)

    mock_record.assert_called_once()
    assert mock_record.call_args.kwargs["telegram_user_id"] == 55555
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_crisis_response_sent_even_if_safety_event_fails() -> None:
    """C-9: crisis response is still sent when SafetyEvent DB write raises."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("я хочу умереть", user_id=66666)
    mock_record = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    with (
        patch("app.bot.handlers.chat.record_safety_event", mock_record),
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_safe_response_content_forwarded_to_user() -> None:
    """C-10: a clean LLM response passes output validation and is sent verbatim to the user."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Как снизить тревогу?", user_id=88001)

    fake_response = MagicMock()
    fake_response.content = "Попробуй дыхательное упражнение: вдох 4 счёта, выдох 6 счётов."

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.NO_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once_with(fake_response.content)


@pytest.mark.asyncio
async def test_output_validator_not_called_without_consent() -> None:
    """C-11: validate_support_response is never called when the user has no consent."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Привет", user_id=88002)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.OpenRouterClient"),
        patch("app.bot.handlers.chat.validate_support_response") as mock_validator,
    ):
        await handle_message(msg)

    mock_validator.assert_not_called()


@pytest.mark.asyncio
async def test_classifier_429_returns_rate_limited_message() -> None:
    """C-12: HTTP 429 from classifier returns chat.rate_limited, not chat.error."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("Мне тяжело", user_id=42001)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(side_effect=_make_http_status_error(429))

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    assert msg.answer.call_args.args[0] == get_text("chat.rate_limited", "en")


@pytest.mark.asyncio
async def test_classifier_non_429_http_error_fails_closed() -> None:
    """C-13: non-429 HTTP error from classifier uses chat.error (fail closed)."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("Мне тяжело", user_id=42002)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(side_effect=_make_http_status_error(503))

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    assert msg.answer.call_args.args[0] == get_text("chat.error", "en")


@pytest.mark.asyncio
async def test_crisis_before_consent_no_classifier_no_llm() -> None:
    """C-14: deterministic crisis fires before consent gate — classifier and LLM never called."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("я хочу умереть", user_id=42003)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_classifier.classify.assert_not_called()
    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
