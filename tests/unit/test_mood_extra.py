"""Extra tests for Mood Journal: history, notes, trend, summary after note save (MX-1..MX-7)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_callback(data: str, user_id: int = 2001, lang: str = "en") -> MagicMock:
    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = lang

    callback = MagicMock()
    callback.data = data
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _fake_entry(score: int, note: str = "", days_ago: int = 0) -> MagicMock:
    entry = MagicMock()
    entry.mood_score = score
    entry.notes = note or None
    dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)
    entry.created_at = dt
    return entry


# ── MX-1: After note save, summary card is displayed ─────────────────────────

@pytest.mark.asyncio
async def test_after_note_save_summary_card_shown() -> None:
    """MX-1: send_mood_summary sends a card with summary text and action keyboard."""
    from app.bot.handlers.mood import send_mood_summary

    user_id = 2001
    fake_entry = _fake_entry(score=4)

    msg = MagicMock()
    msg.answer = AsyncMock()

    mock_history = AsyncMock(return_value=[fake_entry])
    with patch("app.bot.handlers.mood.get_mood_history", mock_history):
        await send_mood_summary(msg, user_id, "en")

    msg.answer.assert_called_once()
    kwargs = msg.answer.call_args.kwargs
    keyboard = kwargs.get("reply_markup") or msg.answer.call_args.args[1]
    datas = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "mood_history" in datas
    assert "mood_trend" in datas
    assert "mood_notes" in datas
    assert "back_to_menu" in datas


# ── MX-2: History view returns saved entries ─────────────────────────────────

@pytest.mark.asyncio
async def test_mood_history_view_shows_entries() -> None:
    """MX-2: on_mood_history shows entry dates, scores, and note previews."""
    from app.bot.handlers.mood import on_mood_history

    callback = _make_callback("mood_history", user_id=2002)
    entries = [_fake_entry(4, "Great day", 0), _fake_entry(3, "", 1)]

    with patch("app.bot.handlers.mood.get_mood_history", AsyncMock(return_value=entries)):
        await on_mood_history(callback)

    callback.message.edit_text.assert_called_once()
    text = callback.message.edit_text.call_args.args[0]
    assert "4/5" in text
    assert "Great day" in text
    callback.answer.assert_called_once()


# ── MX-3: History view shows empty state when no entries ─────────────────────

@pytest.mark.asyncio
async def test_mood_history_view_empty_state() -> None:
    """MX-3: on_mood_history shows empty state when no entries exist."""
    from app.bot.handlers.mood import on_mood_history

    callback = _make_callback("mood_history", user_id=2003)

    with patch("app.bot.handlers.mood.get_mood_history", AsyncMock(return_value=[])):
        await on_mood_history(callback)

    text = callback.message.edit_text.call_args.args[0]
    assert "no entries" in text.lower() or "empty" in text.lower() or "нет" in text.lower()


# ── MX-4: Notes view shows notes with previews ───────────────────────────────

@pytest.mark.asyncio
async def test_mood_notes_view_shows_notes() -> None:
    """MX-4: on_mood_notes shows note text for entries that have notes."""
    from app.bot.handlers.mood import on_mood_notes

    callback = _make_callback("mood_notes", user_id=2004)
    entries = [
        _fake_entry(5, "Felt really good today", 0),
        _fake_entry(3, "", 1),
        _fake_entry(4, "Project going well", 2),
    ]

    with patch("app.bot.handlers.mood.get_mood_history", AsyncMock(return_value=entries)):
        await on_mood_notes(callback)

    text = callback.message.edit_text.call_args.args[0]
    assert "Felt really good today" in text
    assert "Project going well" in text
    callback.answer.assert_called_once()


# ── MX-5: Notes view shows empty state when no notes ─────────────────────────

@pytest.mark.asyncio
async def test_mood_notes_view_empty_state() -> None:
    """MX-5: on_mood_notes shows empty message when no entries have notes."""
    from app.bot.handlers.mood import on_mood_notes

    callback = _make_callback("mood_notes", user_id=2005)
    entries = [_fake_entry(3, "", 0), _fake_entry(4, "", 1)]

    with patch("app.bot.handlers.mood.get_mood_history", AsyncMock(return_value=entries)):
        await on_mood_notes(callback)

    text = callback.message.edit_text.call_args.args[0]
    assert "no notes" in text.lower() or "empty" in text.lower() or "нет" in text.lower()


# ── MX-6: Trend view needs at least 3 entries ────────────────────────────────

@pytest.mark.asyncio
async def test_mood_trend_view_needs_more_entries() -> None:
    """MX-6: on_mood_trend tells user more entries needed when count < 3."""
    from app.bot.handlers.mood import on_mood_trend

    callback = _make_callback("mood_trend", user_id=2006)

    for count in (0, 1, 2):
        entries = [_fake_entry(4) for _ in range(count)]
        trend_data = {
            "count": count,
            "entries": entries,
            **({"avg": 4.0, "high": 4, "low": 4} if entries else {}),
        }
        with patch("app.bot.handlers.mood.get_mood_trend_data", AsyncMock(return_value=trend_data)):
            await on_mood_trend(callback)

        text = callback.message.edit_text.call_args.args[0]
        assert "3" in text or "need" in text.lower() or "нужно" in text.lower(), \
            f"count={count}: expected 'need more entries' message"


# ── MX-7: Trend view shows insight when enough entries ───────────────────────

@pytest.mark.asyncio
async def test_mood_trend_view_shows_insight_with_enough_data() -> None:
    """MX-7: on_mood_trend shows average, high, low, and trend insight with 3+ entries."""
    from app.bot.handlers.mood import on_mood_trend

    callback = _make_callback("mood_trend", user_id=2007)
    entries = [_fake_entry(5), _fake_entry(4), _fake_entry(3)]
    trend_data = {"count": 3, "entries": entries, "avg": 4.0, "high": 5, "low": 3}

    with patch("app.bot.handlers.mood.get_mood_trend_data", AsyncMock(return_value=trend_data)):
        await on_mood_trend(callback)

    text = callback.message.edit_text.call_args.args[0]
    assert "4.0" in text
    assert "5" in text
    assert "3" in text
