"""Integration tests for FriendlyConversationAgent and Talk Mode handler routing.

FC-1: MODE_FRIENDLY_CHAT routes to FriendlyConversationAgent (not SupportPipeline)
FC-2: First friendly response carries no inline keyboard
FC-3: Turns 1–4 carry no inline feedback keyboard
FC-4: Turn 5 surfaces feedback inline keyboard
FC-5: score_talk_humanness is invoked for every friendly response
FC-6: Repair pass triggers when scorer flags a generic/mechanical response
FC-7: FriendlyConversationAgent.run returns a PipelineResult with content
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.orchestration.models import PipelineResult, RiskTier
from app.ai.agents.friendly_conversation import FriendlyConversationAgent


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_message(user_id: int, text: str) -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "ru"
    from_user.id = user_id

    msg = MagicMock()
    msg.text = text
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()
    return msg


def _mock_llm_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    return resp


def _handler_context(mock_client, *, model: str = "test-model"):
    """Return the standard patch stack for handle_message tests."""
    from contextlib import ExitStack
    stack = ExitStack()
    stack.enter_context(
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True)
    )
    stack.enter_context(
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client)
    )
    settings_mock = stack.enter_context(patch("app.bot.handlers.chat.settings"))
    settings_mock.classifier_model = None
    settings_mock.default_model = model
    settings_mock.fallback_models = []
    settings_mock.tracing_salt = MagicMock()
    settings_mock.tracing_salt.get_secret_value.return_value = "test-salt"
    return stack


# ── FC-1: Routing ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_friendly_mode_routes_to_friendly_agent() -> None:
    """FC-1: MODE_FRIENDLY_CHAT uses FriendlyConversationAgent, not SupportPipeline."""
    from app.bot.handlers.chat import handle_message, _friendly_exchange_count
    from app.bot.user_state import MODE_FRIENDLY_CHAT, set_mode

    user_id = 70001
    set_mode(user_id, MODE_FRIENDLY_CHAT)
    _friendly_exchange_count.pop(user_id, None)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Расскажи. Что случилось?")
    )

    msg = _make_message(user_id, "мне плохо")

    with _handler_context(mock_client):
        with patch(
            "app.ai.agents.friendly_conversation.FriendlyConversationAgent.run",
            new_callable=AsyncMock,
            return_value=PipelineResult(
                content="Расскажи. Что случилось?",
                is_safe=True,
                block_reason=None,
                scenario_id="friendly_conversation",
                technique_id=None,
                risk_tier=RiskTier.TIER_1,
                intake_language="ru",
            ),
        ) as mock_agent_run:
            with patch(
                "app.ai.orchestration.pipeline.SupportPipeline.run",
                new_callable=AsyncMock,
            ) as mock_pipeline_run:
                await handle_message(msg)

    mock_agent_run.assert_called_once()
    mock_pipeline_run.assert_not_called()


# ── FC-2/3/4: Keyboard policy ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_friendly_turn_has_no_inline_keyboard() -> None:
    """FC-2: First turn in friendly mode — reply_markup must be None."""
    from app.bot.handlers.chat import handle_message, _friendly_exchange_count
    from app.bot.user_state import MODE_FRIENDLY_CHAT, set_mode

    user_id = 70002
    set_mode(user_id, MODE_FRIENDLY_CHAT)
    _friendly_exchange_count.pop(user_id, None)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Расскажи. Что случилось?")
    )

    msg = _make_message(user_id, "мне плохо")

    with _handler_context(mock_client):
        await handle_message(msg)

    msg.answer.assert_called_once()
    _, kwargs = msg.answer.call_args
    assert kwargs.get("reply_markup") is None, (
        "First friendly turn must send no inline keyboard"
    )


@pytest.mark.asyncio
async def test_turns_1_to_4_have_no_feedback_inline_keyboard() -> None:
    """FC-3: Turns 1–4 must all have reply_markup=None (no inline feedback buttons)."""
    from app.bot.handlers.chat import handle_message, _friendly_exchange_count, _FEEDBACK_EVERY_N
    from app.bot.user_state import MODE_FRIENDLY_CHAT, set_mode

    user_id = 70003
    set_mode(user_id, MODE_FRIENDLY_CHAT)
    _friendly_exchange_count.pop(user_id, None)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Слышу тебя.")
    )

    for turn in range(1, _FEEDBACK_EVERY_N):  # turns 1..4
        msg = _make_message(user_id, f"сообщение {turn}")
        with _handler_context(mock_client):
            await handle_message(msg)
        _, kwargs = msg.answer.call_args
        assert kwargs.get("reply_markup") is None, (
            f"Turn {turn} must have no inline keyboard, got: {kwargs.get('reply_markup')}"
        )


@pytest.mark.asyncio
async def test_fifth_turn_surfaces_feedback_keyboard() -> None:
    """FC-4: Turn 5 must include an inline feedback keyboard."""
    from app.bot.handlers.chat import handle_message, _friendly_exchange_count, _FEEDBACK_EVERY_N
    from app.bot.user_state import MODE_FRIENDLY_CHAT, set_mode
    from aiogram import types

    user_id = 70004
    set_mode(user_id, MODE_FRIENDLY_CHAT)
    _friendly_exchange_count.pop(user_id, None)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Слышу тебя.")
    )

    for turn in range(1, _FEEDBACK_EVERY_N + 1):
        msg = _make_message(user_id, f"сообщение {turn}")
        with _handler_context(mock_client):
            await handle_message(msg)

    _, kwargs = msg.answer.call_args
    kb = kwargs.get("reply_markup")
    assert kb is not None, f"Turn {_FEEDBACK_EVERY_N} must show feedback keyboard"
    assert isinstance(kb, types.InlineKeyboardMarkup)


# ── FC-5: score_talk_humanness is called ─────────────────────────────────────


@pytest.mark.asyncio
async def test_talk_humanness_scorer_called_for_friendly_response() -> None:
    """FC-5: score_talk_humanness must be invoked on every friendly agent draft."""
    mock_client = MagicMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Расскажи. Что случилось?")
    )

    agent = FriendlyConversationAgent(mock_client, model="test-model")

    with patch(
        "app.ai.agents.friendly_conversation.score_talk_humanness",
        wraps=__import__(
            "app.ai.orchestration.talk_humanization", fromlist=["score_talk_humanness"]
        ).score_talk_humanness,
    ) as mock_score:
        await agent.run("мне плохо", "ru", [])

    mock_score.assert_called_once()


# ── FC-6: Repair pass on mechanical response ─────────────────────────────────


@pytest.mark.asyncio
async def test_repair_pass_triggers_on_mechanical_draft() -> None:
    """FC-6: When scorer flags a generic/mechanical draft, repair pass must run."""
    mechanical = (
        "Я слышу, что тебе сейчас плохо. "
        "Твои чувства важны и понятны. "
        "Это совершенно нормально чувствовать боль. "
        "Что именно тебя беспокоит больше всего?"
    )
    repaired = "Тяжело. Расскажи, что произошло?"

    call_count = 0

    async def _side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.content = mechanical if call_count == 1 else repaired
        return resp

    mock_client = MagicMock()
    mock_client.chat_completion = AsyncMock(side_effect=_side_effect)

    agent = FriendlyConversationAgent(mock_client, model="test-model")
    result = await agent.run("мне плохо", "ru", [])

    # Two LLM calls: draft + repair
    assert mock_client.chat_completion.call_count == 2, (
        "Repair pass must trigger a second LLM call when draft is mechanical"
    )
    assert result.content == repaired


# ── FC-7: FriendlyConversationAgent.run contract ─────────────────────────────


@pytest.mark.asyncio
async def test_friendly_agent_run_returns_safe_pipeline_result() -> None:
    """FC-7: FriendlyConversationAgent.run must return a safe PipelineResult."""
    mock_client = MagicMock()
    mock_client.chat_completion = AsyncMock(
        return_value=_mock_llm_response("Расскажи. Что случилось?")
    )

    agent = FriendlyConversationAgent(mock_client, model="test-model")
    result = await agent.run("мне плохо", "ru", [])

    assert isinstance(result, PipelineResult)
    assert result.is_safe
    assert result.content
    assert result.scenario_id == "friendly_conversation"
