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
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()
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
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test/classifier"
        mock_settings.fallback_models = []
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    mock_client.close.assert_called()


@pytest.mark.asyncio
async def test_system_prompt_used_in_chat_completion() -> None:
    """C-1: LLM receives a system message with safety rules, not the raw model name."""
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
    # Pipeline builds a dynamic prompt — verify it contains core safety content
    assert "не врач" in system_msg["content"] or "самопомощи" in system_msg["content"]
    assert system_msg["content"] != "openrouter/free"
    assert len(system_msg["content"]) > 100


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

    msg.answer.assert_called_once()
    assert msg.answer.call_args.args[0] == fake_response.content


@pytest.mark.asyncio
async def test_output_validator_not_called_without_consent() -> None:
    """C-11: output validation is never reached when the user has no consent."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Привет", user_id=88002)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.OpenRouterClient"),
        # validate_support_response now lives inside the pipeline; patch it there
        patch("app.ai.orchestration.pipeline.validate_support_response") as mock_validator,
    ):
        await handle_message(msg)

    mock_validator.assert_not_called()


@pytest.mark.asyncio
async def test_classifier_429_returns_classifier_unavailable_message() -> None:
    """C-12: HTTP 429 from classifier returns chat.classifier_unavailable (fails closed, never reaches LLM)."""
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
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test/classifier"
        mock_settings.fallback_models = []
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    assert msg.answer.call_args.args[0] == get_text("chat.classifier_unavailable", "en")


@pytest.mark.asyncio
async def test_classifier_non_429_http_error_fails_closed() -> None:
    """C-13: non-429 HTTP error from classifier uses chat.classifier_unavailable (fail closed)."""
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
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test/classifier"
        mock_settings.fallback_models = []
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()
    assert msg.answer.call_args.args[0] == get_text("chat.classifier_unavailable", "en")


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


@pytest.mark.asyncio
async def test_settings_classifier_model_wired_to_classifier() -> None:
    """S-1: settings.classifier_model is passed as model= to SafetyClassifier."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Как дела?", user_id=50001)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.NO_RISK
    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    captured: dict = {}

    def _capture_classifier(client, model=None, fallback_models=None):
        captured["model"] = model
        return mock_classifier

    fake_response = MagicMock()
    fake_response.content = "Всё хорошо!"
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", side_effect=_capture_classifier),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test-model/7b"
        mock_settings.fallback_models = []
        await handle_message(msg)

    assert captured.get("model") == "test-model/7b"


@pytest.mark.asyncio
async def test_empty_classifier_model_does_not_call_classifier() -> None:
    """S-2: empty CLASSIFIER_MODEL → SafetyClassifier is never constructed or called."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Как дела?", user_id=50002)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    fake_response = MagicMock()
    fake_response.content = "Всё хорошо!"
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    mock_classifier_cls = MagicMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", mock_classifier_cls),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = []
        mock_settings.default_model = "test/default"
        await handle_message(msg)

    mock_classifier_cls.assert_not_called()


@pytest.mark.asyncio
async def test_classifier_429_log_has_stage_no_user_id(caplog) -> None:
    """S-5: classifier 429 warning has stage label but does not expose raw user ID."""
    import logging

    from app.bot.handlers.chat import handle_message

    user_id = 50099
    msg = _make_message("Мне тяжело", user_id=user_id)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(side_effect=_make_http_status_error(429))

    with caplog.at_level(logging.WARNING, logger="app.bot.handlers.chat"):
        with (
            patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
            patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
            patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
            patch("app.bot.handlers.chat.settings") as mock_settings,
        ):
            mock_settings.classifier_model = "test/classifier"
            mock_settings.fallback_models = []
            await handle_message(msg)

    assert any("stage=classifier" in r.message for r in caplog.records)
    assert not any(str(user_id) in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_crisis_response_uses_message_language_not_telegram_language() -> None:
    """L-1: English crisis text classified by the LLM classifier gets English crisis response
    even when the Telegram user's preferred language is Russian."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    # Telegram user has Russian language_code but sends English crisis message
    msg = _make_message("everything is hopeless and I cannot go on living", user_id=60001)
    msg.from_user.language_code = "ru"

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.IMMINENT_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test/classifier"
        mock_settings.fallback_models = []
        await handle_message(msg)

    msg.answer.assert_called_once()
    mock_client.chat_completion.assert_not_called()
    # After fix: crisis response language follows message language (en), not Telegram language (ru)
    response_text = msg.answer.call_args.args[0]
    assert response_text == get_text("crisis.response", "en"), (
        "English crisis message should receive English crisis response"
    )


@pytest.mark.asyncio
async def test_imminent_danger_via_classifier_sends_crisis_response_no_llm() -> None:
    """C-15: classifier returning IMMINENT_RISK sends crisis response and skips LLM."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("everything is hopeless and I cannot go on", user_id=61001)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    mock_classification = MagicMock()
    mock_classification.risk_level = RiskLevel.IMMINENT_RISK

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(return_value=mock_classification)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = "test/classifier"
        mock_settings.fallback_models = []
        await handle_message(msg)

    mock_client.chat_completion.assert_not_called()
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_crisis_event_log_does_not_expose_user_id(caplog) -> None:
    """P-1: crisis recording path must not emit raw telegram_user_id in any log record."""
    import logging

    from app.bot.handlers.chat import handle_message

    user_id = 60099
    msg = _make_message("я хочу умереть", user_id=user_id)

    with caplog.at_level(logging.WARNING, logger="app.bot.handlers.chat"):
        with patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock):
            await handle_message(msg)

    assert not any(str(user_id) in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Passive-risk routing — screenshot regression (C-16 through C-20)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text,lang",
    [
        ("I wish I could disappear.", "en"),
        ("I want to disappear", "en"),
        ("I wish I wasn't here", "en"),
        ("I don't want to exist", "en"),
        ("хочу исчезнуть", "ru"),
        ("не хочу существовать", "ru"),
        ("лучше бы меня не было", "ru"),
    ],
)
async def test_passive_risk_phrase_returns_passive_risk_response(text: str, lang: str) -> None:
    """C-16: passive disappearance phrases return crisis.passive_risk, not error fallback."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message(text, user_id=70001)
    msg.from_user.language_code = lang

    with patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock):
        await handle_message(msg)

    msg.answer.assert_called_once()
    response_text = msg.answer.call_args.args[0]
    assert response_text == get_text("crisis.passive_risk", lang), (
        f"Expected passive_risk response for {text!r} ({lang}), got: {response_text!r}"
    )


@pytest.mark.asyncio
async def test_passive_risk_bypasses_classifier_entirely() -> None:
    """C-17: passive-risk phrase must NOT call the LLM classifier — deterministic only."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("I wish I could disappear.", user_id=70002)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()
    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock()

    with (
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    mock_classifier.classify.assert_not_called()
    mock_client.chat_completion.assert_not_called()


@pytest.mark.asyncio
async def test_passive_risk_survives_all_models_rate_limited() -> None:
    """C-18: passive-risk phrase returns passive_risk response even when all OpenRouter models are 429."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("I wish I could disappear.", user_id=70003)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock(side_effect=_make_http_status_error(429))

    with (
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once()
    response_text = msg.answer.call_args.args[0]
    assert response_text == get_text("crisis.passive_risk", "en")


@pytest.mark.asyncio
async def test_passive_risk_fires_before_consent_gate() -> None:
    """C-19: passive-risk routing runs before consent check — no consent required."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("I want to disappear", user_id=70004)

    mock_classifier = MagicMock()
    mock_classifier.classify = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=False),
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.OpenRouterClient"),
        patch("app.bot.handlers.chat.SafetyClassifier", return_value=mock_classifier),
    ):
        await handle_message(msg)

    msg.answer.assert_called_once()
    mock_classifier.classify.assert_not_called()
    assert msg.answer.call_args.args[0] == get_text("crisis.passive_risk", "en")


@pytest.mark.asyncio
async def test_passive_risk_response_not_generic_error() -> None:
    """C-20: passive-risk response must not be the classifier_unavailable or generic error text."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("I wish I could disappear.", user_id=70005)

    with patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock):
        await handle_message(msg)

    msg.answer.assert_called_once()
    response_text = msg.answer.call_args.args[0]
    assert response_text != get_text("chat.classifier_unavailable", "en")
    assert response_text != get_text("chat.error", "en")


# ---------------------------------------------------------------------------
# Normal support generation path — N-1 through N-5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normal_english_message_reaches_support_generation() -> None:
    """N-1: normal English message with classifier disabled reaches the support pipeline."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("I feel anxious", user_id=80001)
    msg.from_user.language_code = "en"

    fake_response = MagicMock()
    fake_response.content = "I hear you. Let's work through this together."
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = []
        mock_settings.default_model = "google/gemini-2.5-flash-lite"
        await handle_message(msg)

    mock_client.chat_completion.assert_called_once()
    msg.answer.assert_called()
    assert msg.answer.call_args.args[0] == fake_response.content


@pytest.mark.asyncio
async def test_normal_russian_message_reaches_support_generation() -> None:
    """N-2: normal Russian message with classifier disabled reaches the support pipeline."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("Мне грустно и тяжело", user_id=80002)
    msg.from_user.language_code = "ru"

    fake_response = MagicMock()
    fake_response.content = "Я здесь, расскажи что происходит."
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = []
        mock_settings.default_model = "google/gemini-2.5-flash-lite"
        await handle_message(msg)

    mock_client.chat_completion.assert_called_once()
    msg.answer.assert_called()
    assert msg.answer.call_args.args[0] == fake_response.content


@pytest.mark.asyncio
async def test_pipeline_429_triggers_fallback_model() -> None:
    """N-3: HTTP 429 from primary model triggers the fallback model for support generation."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("I feel anxious", user_id=80003)

    fake_response = MagicMock()
    fake_response.content = "Here is some support."
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(
        side_effect=[_make_http_status_error(429), fake_response]
    )

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = ["google/gemini-2.5-flash"]
        mock_settings.default_model = "google/gemini-2.5-flash-lite"
        await handle_message(msg)

    assert mock_client.chat_completion.call_count == 2
    msg.answer.assert_called()
    assert msg.answer.call_args.args[0] == fake_response.content


@pytest.mark.asyncio
async def test_all_pipeline_failures_return_generic_error_not_crisis() -> None:
    """N-4: all model failures return chat.error, not a crisis or passive-risk response."""
    from app.bot.handlers.chat import handle_message
    from app.bot.handlers.i18n import get_text

    msg = _make_message("I feel anxious", user_id=80004)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(side_effect=_make_http_status_error(429))

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = ["google/gemini-2.5-flash"]
        mock_settings.default_model = "google/gemini-2.5-flash-lite"
        await handle_message(msg)

    msg.answer.assert_called_once()
    response_text = msg.answer.call_args.args[0]
    assert response_text != get_text("crisis.response", "en")
    assert response_text != get_text("crisis.passive_risk", "en")
    assert response_text == get_text("chat.error", "en")


@pytest.mark.asyncio
async def test_free_text_after_start_reaches_support_pipeline() -> None:
    """N-5: free text sent after /start (consent granted) reaches the support pipeline."""
    from app.bot.handlers.chat import handle_message

    msg = _make_message("I broke up with someone and it hurts badly", user_id=80005)
    msg.from_user.language_code = "en"

    fake_response = MagicMock()
    fake_response.content = "I'm sorry to hear that. Breakups can be really painful."
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value=fake_response)

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = ""
        mock_settings.fallback_models = []
        mock_settings.default_model = "google/gemini-2.5-flash-lite"
        await handle_message(msg)

    mock_client.chat_completion.assert_called_once()
    msg.answer.assert_called()
    assert msg.answer.call_args.args[0] == fake_response.content
