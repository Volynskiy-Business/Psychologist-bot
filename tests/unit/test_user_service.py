"""Tests for user_service — upsert, consent persistence, and DB-backed consent check."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import User
from app.services.user_service import grant_consent, has_consent, upsert_user


def _mock_session(scalar_result=None):
    """Mock session with only the awaited methods as AsyncMock."""
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = scalar_result
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _session_factory(session):
    """Async context-manager factory that yields the given session."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=ctx)


# ── Test 1: consent is persisted when consent_agree callback is handled ────────

@pytest.mark.asyncio
async def test_on_consent_agree_persists_consent() -> None:
    """T-1: on_consent_agree handler calls grant_consent with the correct telegram_id."""
    from app.bot.handlers.start import on_consent_agree

    callback = MagicMock()
    callback.from_user.id = 12345
    callback.from_user.username = "alice"
    callback.from_user.first_name = "Alice"
    callback.from_user.language_code = "en"
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    mock_grant = AsyncMock()

    with patch("app.bot.handlers.start.grant_consent", mock_grant):
        await on_consent_agree(callback)

    mock_grant.assert_called_once()
    assert mock_grant.call_args.kwargs["telegram_id"] == 12345


# ── Test 2: user is created when missing ──────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_creates_user_when_missing() -> None:
    """T-2: upsert_user inserts a new User row when no existing record is found."""
    session = _mock_session(scalar_result=None)

    user = await upsert_user(session, telegram_id=42, username="alice", language="en")

    session.add.assert_called_once()
    assert user.telegram_id == 42
    assert user.username == "alice"
    assert user.language == "en"


# ── Test 3: existing user is reused ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_reuses_existing_user() -> None:
    """T-3: upsert_user updates fields on an existing user and does not INSERT."""
    original_time = datetime(2026, 1, 1)
    existing = User(
        telegram_id=42,
        username="old_name",
        language="ru",
        consent_given=True,
        consent_accepted_at=original_time,
        created_at=original_time,
        updated_at=original_time,
    )
    session = _mock_session(scalar_result=existing)

    user = await upsert_user(session, telegram_id=42, username="new_name", language="en")

    session.add.assert_not_called()
    assert user is existing
    assert user.username == "new_name"
    assert user.language == "en"
    assert user.consent_given is True  # consent fields untouched


# ── Test 4: existing consent_accepted_at is not erased ───────────────────────

@pytest.mark.asyncio
async def test_grant_consent_preserves_first_accepted_at() -> None:
    """T-4: grant_consent does not overwrite consent_accepted_at once set."""
    original_time = datetime(2026, 1, 1, 12, 0, 0)
    existing = User(
        telegram_id=42,
        username="alice",
        language="en",
        consent_given=True,
        consent_accepted_at=original_time,
        created_at=original_time,
        updated_at=original_time,
    )
    session = _mock_session(scalar_result=existing)

    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        await grant_consent(telegram_id=42)

    assert existing.consent_accepted_at == original_time


# ── Tests 5–7 are in test_chat_handler.py (handle_message consent gate / crisis) ──

# ── Additional service tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grant_consent_sets_accepted_at_for_new_user() -> None:
    """New user gets consent_accepted_at stamped when grant_consent is called."""
    session = _mock_session(scalar_result=None)

    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        await grant_consent(telegram_id=99, username="bob", language="ru")

    added_user = session.add.call_args[0][0]
    assert added_user.consent_given is True
    assert added_user.consent_accepted_at is not None


@pytest.mark.asyncio
async def test_has_consent_returns_true_for_consented_user() -> None:
    session = _mock_session(scalar_result=True)

    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        result = await has_consent(42)

    assert result is True


@pytest.mark.asyncio
async def test_has_consent_returns_false_when_user_missing() -> None:
    session = _mock_session(scalar_result=None)

    with patch("app.services.user_service.AsyncSessionLocal", _session_factory(session)):
        result = await has_consent(999)

    assert result is False
