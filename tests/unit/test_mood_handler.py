"""Tests for mood handler — MoodEntry persistence (M-1..M-3) and note flow (M-4)."""

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


def _make_add_note_callback(user_id: int = 55) -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    callback = MagicMock()
    callback.data = "add_mood_note"
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_add_note_callback_sets_pending_state() -> None:
    """M-3: clicking 'Add a note' marks the user as awaiting a note and shows the prompt."""
    import app.bot.handlers.mood as mood_module
    from app.bot.handlers.mood import on_mood_add_note

    callback = _make_add_note_callback(user_id=55)
    mood_module._awaiting_note.discard(55)  # start clean

    await on_mood_add_note(callback)

    assert mood_module.is_awaiting_note(55)
    callback.message.edit_text.assert_called_once()
    prompt_text = callback.message.edit_text.call_args.args[0]
    assert "note" in prompt_text.lower()
    callback.answer.assert_called_once()

    mood_module._awaiting_note.discard(55)  # cleanup


@pytest.mark.asyncio
async def test_chat_handler_captures_mood_note() -> None:
    """M-4: when user is awaiting a note, handle_message saves it and skips LLM."""
    import app.bot.handlers.mood as mood_module
    from app.bot.handlers.chat import handle_message

    user_id = 77
    mood_module._awaiting_note.add(user_id)

    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    msg = MagicMock()
    msg.text = "Felt calm after morning walk"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    mock_save_note = AsyncMock()

    with (
        patch("app.bot.handlers.chat.deterministic_crisis_check", return_value=(0, None)),
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.save_mood_note", mock_save_note),
        patch("app.bot.handlers.chat.OpenRouterClient") as mock_client_cls,
    ):
        await handle_message(msg)

    mock_save_note.assert_called_once_with(user_id, "Felt calm after morning walk")
    assert not mood_module.is_awaiting_note(user_id)
    mock_client_cls.assert_not_called()  # LLM must not be invoked
    msg.answer.assert_called_once()
