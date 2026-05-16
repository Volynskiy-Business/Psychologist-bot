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
    # SELECT user, DELETE feedback, DELETE mood_entries, DELETE messages,
    # SELECT safety_plan, DELETE safety_plan_items, DELETE safety_plans,
    # UPDATE safety_events — 8 execute calls total
    assert session.execute.call_count == 8
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
    """D-6: deletes mood_entries, messages, safety_plan_items, safety_plans; UPDATE nullifies safety_events."""
    from app.services.user_service import delete_user_data

    fake_user = MagicMock()
    fake_user.id = 7

    session = _mock_session(user=fake_user)
    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        await delete_user_data(42)

    from sqlalchemy.sql.dml import Delete, Update

    stmts = [call.args[0] for call in session.execute.call_args_list]
    assert len(stmts) == 8

    delete_tables = {s.table.name for s in stmts if isinstance(s, Delete)}
    update_tables = {s.table.name for s in stmts if isinstance(s, Update)}

    assert delete_tables == {"feedback", "mood_entries", "messages", "safety_plan_items", "safety_plans"}
    assert update_tables == {"safety_events"}


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
