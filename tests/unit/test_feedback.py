"""Tests for the feedback button system (FB-1..FB-5)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_callback(data: str, user_id: int = 3001, lang: str = "en") -> MagicMock:
    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = lang

    callback = MagicMock()
    callback.data = data
    callback.from_user = from_user
    callback.message.edit_reply_markup = AsyncMock()
    callback.answer = AsyncMock()
    return callback


# ── FB-1: feedback_keyboard has thumbs-up and thumbs-down buttons ─────────────

def test_feedback_keyboard_has_both_buttons() -> None:
    """FB-1: feedback_keyboard includes fbk_y and fbk_n callback buttons."""
    from app.bot.handlers.feedback import feedback_keyboard

    kb = feedback_keyboard("en")
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "fbk_y" in all_data
    assert "fbk_n" in all_data


# ── FB-2: feedback_keyboard has back-to-menu button ──────────────────────────

def test_feedback_keyboard_has_back_to_menu() -> None:
    """FB-2: feedback_keyboard includes back_to_menu button."""
    from app.bot.handlers.feedback import feedback_keyboard

    kb = feedback_keyboard("ru")
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "back_to_menu" in all_data


# ── FB-3: on_feedback records helpful=True for fbk_y ─────────────────────────

@pytest.mark.asyncio
async def test_on_feedback_records_helpful() -> None:
    """FB-3: on_feedback calls record_response_feedback with helpful=True on fbk_y."""
    from app.bot.handlers.feedback import on_feedback

    callback = _make_callback("fbk_y")
    with patch(
        "app.bot.handlers.feedback.record_response_feedback", new_callable=AsyncMock
    ) as mock_record:
        await on_feedback(callback)

    mock_record.assert_awaited_once_with(3001, True)
    callback.message.edit_reply_markup.assert_awaited_once()
    callback.answer.assert_awaited_once()


# ── FB-4: on_feedback records helpful=False for fbk_n ────────────────────────

@pytest.mark.asyncio
async def test_on_feedback_records_not_helpful() -> None:
    """FB-4: on_feedback calls record_response_feedback with helpful=False on fbk_n."""
    from app.bot.handlers.feedback import on_feedback

    callback = _make_callback("fbk_n")
    with patch(
        "app.bot.handlers.feedback.record_response_feedback", new_callable=AsyncMock
    ) as mock_record:
        await on_feedback(callback)

    mock_record.assert_awaited_once_with(3001, False)


# ── FB-5: on_feedback removes feedback buttons after click ────────────────────

@pytest.mark.asyncio
async def test_on_feedback_removes_feedback_buttons() -> None:
    """FB-5: after recording, only back-to-menu button remains in the keyboard."""
    from app.bot.handlers.feedback import on_feedback

    callback = _make_callback("fbk_y", lang="ru")
    with patch(
        "app.bot.handlers.feedback.record_response_feedback", new_callable=AsyncMock
    ):
        await on_feedback(callback)

    # edit_reply_markup was called once; verify the keyboard has no fbk_ buttons
    call_kwargs = callback.message.edit_reply_markup.call_args
    kb = call_kwargs.kwargs.get("reply_markup") or call_kwargs.args[0]
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "fbk_y" not in all_data
    assert "fbk_n" not in all_data
    assert "back_to_menu" in all_data
