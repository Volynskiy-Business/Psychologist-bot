"""Tests for mood handler — MoodEntry persistence (M-1, M-2)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_callback(mood_score: int, user_id: int = 12345) -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    callback = MagicMock()
    callback.data = f"mood_{mood_score}"
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_mood_selected_saves_entry() -> None:
    """M-1: selecting a mood score calls save_mood_entry with correct telegram_id and score."""
    from app.bot.handlers.mood import on_mood_selected

    callback = _make_callback(mood_score=3, user_id=42)
    mock_save = AsyncMock()

    with patch("app.bot.handlers.mood.save_mood_entry", mock_save):
        await on_mood_selected(callback)

    mock_save.assert_called_once_with(42, 3)
    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_mood_selected_db_failure_shows_error() -> None:
    """M-2: DB failure shows error message instead of success — does not crash."""
    from app.bot.handlers.mood import on_mood_selected

    callback = _make_callback(mood_score=2, user_id=99)
    mock_save = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    with patch("app.bot.handlers.mood.save_mood_entry", mock_save):
        await on_mood_selected(callback)

    # Handler must not crash and must still send a message and ack the callback
    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()
    # Success text contains "Saved"; error path must not
    edit_call = callback.message.edit_text.call_args
    response_text = edit_call.args[0] if edit_call.args else edit_call.kwargs.get("text", "")
    assert "Saved" not in response_text
