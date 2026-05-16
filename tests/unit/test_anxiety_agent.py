"""Tests for AnxietySupportAgent, MODE_ANXIETY_SUPPORT routing, and crisis detection.

AX-1: Crisis phrase "жить не хочется" intercepted before any agent
AX-2: Crisis phrase "жить не хочется" intercepted before MODE_FRIENDLY_CHAT
AX-3: "mode_anxiety" button sets MODE_ANXIETY_SUPPORT
AX-4: "back_to_menu" resets MODE_ANXIETY_SUPPORT
AX-5: In MODE_ANXIETY_SUPPORT, short vague message routes to AnxietySupportAgent
AX-6: In MODE_FRIENDLY_CHAT, crisis phrase still intercepted
AX-7: crisis_detector covers all new Level-3 passive-death-wish variants
AX-8: AnxietySupportAgent.build_prompt injects lang
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check


# ── AX-7: New passive-death-wish patterns ────────────────────────────────────

@pytest.mark.parametrize("phrase", [
    "жить не хочется",
    "Жить не хочется совсем",
    "мне не хочется жить",
    "надоело жить",
    "устал жить",
    "устала жить",
    "нет желания жить",
    "жизнь не нужна",
])
def test_passive_death_wish_caught_at_elevated_distress(phrase: str) -> None:
    """AX-7: Each passive death-wish phrase must trigger at least ELEVATED_DISTRESS (Level 2).

    These are idiomatic/passive — assigned Level 2 (not Level 3) so that
    a qualified statement ("жить не хочется, но я ничего не собираюсь делать")
    does not over-trigger POSSIBLE_CRISIS. Both levels cause early return before any agent.
    """
    risk, pattern = deterministic_crisis_check(phrase)
    assert risk >= RiskLevel.ELEVATED_DISTRESS, (
        f"Expected at least ELEVATED_DISTRESS for '{phrase}', got {risk}"
    )
    assert pattern is not None


# ── AX-1: Crisis intercepted before MODE_ANXIETY_SUPPORT routing ─────────────

@pytest.mark.asyncio
async def test_crisis_phrase_intercepted_before_anxiety_agent() -> None:
    """AX-1: 'жить не хочется' triggers ELEVATED_DISTRESS — early return before anxiety agent."""
    from app.bot.handlers.chat import handle_message
    from app.bot.user_state import MODE_ANXIETY_SUPPORT, set_mode

    user_id = 55001
    set_mode(user_id, MODE_ANXIETY_SUPPORT)

    from_user = MagicMock()
    from_user.language_code = "ru"
    from_user.id = user_id

    msg = MagicMock()
    msg.text = "жить не хочется"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
    ):
        mock_settings.classifier_model = None
        mock_settings.default_model = "test-model"
        mock_settings.fallback_models = []

        await handle_message(msg)

    # crisis path answers and returns — LLM must NOT be called
    msg.answer.assert_called_once()
    mock_client.chat_completion.assert_not_called()


# ── AX-2: Crisis intercepted before MODE_FRIENDLY_CHAT routing ───────────────

@pytest.mark.asyncio
async def test_crisis_phrase_intercepted_before_friendly_agent() -> None:
    """AX-2: Passive death-wish triggers early return before FriendlyConversationAgent."""
    from app.bot.handlers.chat import handle_message
    from app.bot.user_state import MODE_FRIENDLY_CHAT, set_mode

    user_id = 55002
    set_mode(user_id, MODE_FRIENDLY_CHAT)

    from_user = MagicMock()
    from_user.language_code = "ru"
    from_user.id = user_id

    msg = MagicMock()
    msg.text = "не хочется жить совсем"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    mock_client.chat_completion = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.settings") as mock_settings,
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
    ):
        mock_settings.classifier_model = None
        mock_settings.default_model = "test-model"
        mock_settings.fallback_models = []

        await handle_message(msg)

    msg.answer.assert_called_once()
    mock_client.chat_completion.assert_not_called()


# ── AX-3: mode_anxiety button sets MODE_ANXIETY_SUPPORT ──────────────────────

@pytest.mark.asyncio
async def test_mode_anxiety_button_sets_anxiety_support_mode() -> None:
    """AX-3: Tapping '😰 Мне тревожно' stores MODE_ANXIETY_SUPPORT for the user."""
    from app.bot.handlers.start import on_mode_anxiety
    from app.bot.user_state import MODE_ANXIETY_SUPPORT, get_mode

    user_id = 55003

    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    callback = MagicMock()
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    await on_mode_anxiety(callback)

    assert get_mode(user_id) == MODE_ANXIETY_SUPPORT


# ── AX-4: back_to_menu resets MODE_ANXIETY_SUPPORT ───────────────────────────

@pytest.mark.asyncio
async def test_back_to_menu_resets_anxiety_support_mode() -> None:
    """AX-4: 'Back to menu' clears MODE_ANXIETY_SUPPORT."""
    from app.bot.handlers.start import on_back_to_menu
    from app.bot.user_state import MODE_ANXIETY_SUPPORT, get_mode, set_mode

    user_id = 55004
    set_mode(user_id, MODE_ANXIETY_SUPPORT)

    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    callback = MagicMock()
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    await on_back_to_menu(callback)

    assert get_mode(user_id) == ""


# ── AX-5: Short vague message in anxiety mode routes to AnxietySupportAgent ──

@pytest.mark.asyncio
async def test_short_message_in_anxiety_mode_routes_to_anxiety_agent() -> None:
    """AX-5: 'помоги' after anxiety button uses AnxietySupportAgent, not SupportPipeline."""
    from app.bot.handlers.chat import handle_message
    from app.bot.user_state import MODE_ANXIETY_SUPPORT, set_mode
    from app.ai.orchestration.models import PipelineResult, RiskTier

    user_id = 55005
    set_mode(user_id, MODE_ANXIETY_SUPPORT)

    from_user = MagicMock()
    from_user.language_code = "ru"
    from_user.id = user_id

    msg = MagicMock()
    msg.text = "помоги"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    fake_result = PipelineResult(
        content="Я рядом. Давай снизим напряжение.",
        is_safe=True,
        block_reason=None,
        scenario_id="anxiety_support",
        technique_id=None,
        risk_tier=RiskTier.TIER_1,
        intake_language="ru",
    )

    mock_anxiety_agent = MagicMock()
    mock_anxiety_agent.run = AsyncMock(return_value=fake_result)

    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    with (
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.OpenRouterClient", return_value=mock_client),
        patch("app.bot.handlers.chat.AnxietySupportAgent", return_value=mock_anxiety_agent),
        patch("app.bot.handlers.chat.settings") as mock_settings,
    ):
        mock_settings.classifier_model = None
        mock_settings.default_model = "test-model"
        mock_settings.fallback_models = []

        await handle_message(msg)

    mock_anxiety_agent.run.assert_called_once()
    msg.answer.assert_called_once()
    call_text = msg.answer.call_args.args[0]
    assert "рядом" in call_text.lower() or "напряжение" in call_text.lower()


# ── AX-8: AnxietySupportAgent.build_prompt injects lang ─────────────────────

def test_anxiety_agent_build_prompt_injects_lang() -> None:
    """AX-8: build_prompt replaces {lang} placeholder with the given language."""
    from app.ai.agents.anxiety_support import AnxietySupportAgent

    agent = AnxietySupportAgent(client=MagicMock())
    prompt = agent.build_prompt("ru")
    assert "«ru»" in prompt
    assert "{lang}" not in prompt
