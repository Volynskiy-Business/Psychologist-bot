"""Tests for delete_user_data service and on_delete_confirmed handler (D-1 to D-5)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.user_service import DeleteUserDataResult


def _mock_session(user=None):
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = user
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    return session


def _session_factory(session):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=ctx)


def _make_callback(user_id: int = 12345) -> MagicMock:
    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = "en"
    callback = MagicMock()
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


# ── D-1: user not found returns NOT_FOUND ─────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_user_data_not_found() -> None:
    """D-1: returns NOT_FOUND when no user row exists for telegram_user_id."""
    from app.services.user_service import delete_user_data

    session = _mock_session(user=None)
    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        result = await delete_user_data(99999)

    assert result == DeleteUserDataResult.NOT_FOUND
    session.delete.assert_not_called()
    session.commit.assert_not_called()


# ── D-2: user found — deletes rows and commits ────────────────────────────────

@pytest.mark.asyncio
async def test_delete_user_data_deletes_rows_and_commits() -> None:
    """D-2: when user exists, executes bulk deletes and deletes the user row, then commits."""
    from app.services.user_service import delete_user_data

    fake_user = MagicMock()
    fake_user.id = 7

    session = _mock_session(user=fake_user)
    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        result = await delete_user_data(42)

    assert result == DeleteUserDataResult.DELETED
    # bulk deletes: MoodEntry, Message, SafetyEvent update — each is a session.execute call
    # plus the initial SELECT: 4 total execute calls
    assert session.execute.call_count == 4
    session.delete.assert_called_once_with(fake_user)
    session.commit.assert_called_once()


# ── D-3: handler shows success text on DELETED ────────────────────────────────

@pytest.mark.asyncio
async def test_on_delete_confirmed_shows_deleted_text() -> None:
    """D-3: on_delete_confirmed shows privacy.deleted text when deletion succeeds."""
    from app.bot.handlers.start import on_delete_confirmed

    callback = _make_callback(user_id=111)
    mock_delete = AsyncMock(return_value=DeleteUserDataResult.DELETED)

    with patch("app.bot.handlers.start.delete_user_data", mock_delete):
        await on_delete_confirmed(callback)

    mock_delete.assert_called_once_with(111)
    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()
    text_sent = callback.message.edit_text.call_args.args[0]
    assert "deleted" in text_sent.lower() or "удален" in text_sent.lower()


# ── D-4: handler shows not_found text when no data exists ────────────────────

@pytest.mark.asyncio
async def test_on_delete_confirmed_shows_not_found_text() -> None:
    """D-4: on_delete_confirmed shows privacy.not_found text when no data found."""
    from app.bot.handlers.start import on_delete_confirmed

    callback = _make_callback(user_id=222)
    mock_delete = AsyncMock(return_value=DeleteUserDataResult.NOT_FOUND)

    with patch("app.bot.handlers.start.delete_user_data", mock_delete):
        await on_delete_confirmed(callback)

    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()
    text_sent = callback.message.edit_text.call_args.args[0]
    # Must not say data was deleted when it wasn't
    assert "deleted" not in text_sent.lower() or "not found" in text_sent.lower() or "already" in text_sent.lower()


# ── D-6: bulk operations target the correct tables ───────────────────────────

@pytest.mark.asyncio
async def test_delete_targets_correct_tables() -> None:
    """D-6: deletes target mood_entries and messages; SafetyEvent UPDATE sets user_id=None."""
    from app.services.user_service import delete_user_data

    fake_user = MagicMock()
    fake_user.id = 7

    session = _mock_session(user=fake_user)
    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        await delete_user_data(42)

    # Extract statement objects from each execute call (skip the initial SELECT at index 0)
    stmts = [call.args[0] for call in session.execute.call_args_list]
    assert len(stmts) == 4

    bulk_delete_tables = {stmts[1].table.name, stmts[2].table.name}
    assert bulk_delete_tables == {"mood_entries", "messages"}

    assert stmts[3].table.name == "safety_events"


# ── D-5: handler shows error text and does not claim success on DB failure ────

@pytest.mark.asyncio
async def test_on_delete_confirmed_shows_error_on_db_failure() -> None:
    """D-5: on_delete_confirmed shows generic error when delete_user_data raises."""
    from app.bot.handlers.start import on_delete_confirmed

    callback = _make_callback(user_id=333)
    mock_delete = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    with patch("app.bot.handlers.start.delete_user_data", mock_delete):
        await on_delete_confirmed(callback)

    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()
    text_sent = callback.message.edit_text.call_args.args[0]
    # Must not claim success
    assert "deleted" not in text_sent.lower()
    assert "удален" not in text_sent.lower()
