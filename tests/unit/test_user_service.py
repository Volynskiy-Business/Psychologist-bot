"""Tests for user_service — upsert, consent persistence, and DB-backed consent check."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import func, select as sa_select

from app.db.models import Base, Message, MoodEntry, RiskLevel, SafetyEvent, User
from app.services.user_service import (
    DeleteUserDataResult,
    delete_user_data,
    grant_consent,
    has_consent,
    upsert_user,
)

# Fake telegram_id used only in SQLite-backed privacy tests — never a real user.
_TEST_TG_ID = 90_001


async def _make_test_db():
    """Create an in-memory SQLite DB with the full schema. Returns (engine, factory)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    return engine, factory


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


# ── Privacy regression tests (DB-backed) ─────────────────────────────────────
# These use a real SQLite in-memory DB to verify actual column values after
# delete_user_data(), not just call counts.


def _seed_user(tg_id: int, pk: int = 1) -> User:
    # SQLite renders BigInteger PKs as BIGINT NOT NULL + separate PRIMARY KEY(id),
    # which breaks the rowid-alias autoincrement. Set id explicitly for in-memory tests.
    return User(
        id=pk,
        telegram_id=tg_id,
        language="en",
        consent_given=True,
        consent_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _seed_safety_event(user_id, tg_id: int) -> SafetyEvent:
    return SafetyEvent(
        user_id=user_id,
        telegram_user_id=tg_id,
        risk_level=RiskLevel.POSSIBLE_CRISIS,
        risk_type="test",
        confidence=1.0,
        reason="keyword",
        requires_crisis_response=True,
        requires_professional_referral=False,
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_delete_clears_all_identifiers_and_retains_safety_event() -> None:
    """D-P1/D-P2/D-P3: delete_user_data removes user/mood/message rows,
    retains SafetyEvent, and nullifies both user_id and telegram_user_id."""
    engine, factory = await _make_test_db()
    try:
        async with factory() as session:
            user = _seed_user(_TEST_TG_ID)
            session.add(user)
            await session.flush()

            session.add(MoodEntry(
                user_id=user.id, mood_score=3, anxiety_score=5,
                energy_score=5, created_at=datetime.utcnow(),
            ))
            session.add(Message(
                user_id=user.id, role="user",
                content="hello", created_at=datetime.utcnow(),
            ))
            session.add(_seed_safety_event(user.id, _TEST_TG_ID))
            await session.commit()

        with patch("app.services.user_service.AsyncSessionLocal", factory):
            result = await delete_user_data(_TEST_TG_ID)

        assert result == DeleteUserDataResult.DELETED

        async with factory() as session:
            user_count = (await session.execute(
                sa_select(func.count()).select_from(User)
            )).scalar()
            mood_count = (await session.execute(
                sa_select(func.count()).select_from(MoodEntry)
            )).scalar()
            msg_count = (await session.execute(
                sa_select(func.count()).select_from(Message)
            )).scalar()
            safety_count = (await session.execute(
                sa_select(func.count()).select_from(SafetyEvent)
            )).scalar()
            row = (await session.execute(sa_select(SafetyEvent))).scalar_one()

        assert user_count == 0        # D-6: User row deleted
        assert mood_count == 0        # D-4: MoodEntry deleted
        assert msg_count == 0         # D-5: Message deleted
        assert safety_count == 1      # D-1: SafetyEvent retained
        assert row.user_id is None    # D-2: user_id nullified
        assert row.telegram_user_id is None  # D-3: telegram_user_id nullified
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_nullifies_preconsent_safety_event() -> None:
    """D-P4: SafetyEvent created pre-consent (user_id=NULL) also has
    telegram_user_id nullified when the user later deletes their data."""
    engine, factory = await _make_test_db()
    try:
        async with factory() as session:
            user = _seed_user(_TEST_TG_ID)
            session.add(user)
            await session.flush()

            # Pre-consent crisis row: user_id is NULL, telegram_user_id is set.
            session.add(_seed_safety_event(None, _TEST_TG_ID))
            await session.commit()

        with patch("app.services.user_service.AsyncSessionLocal", factory):
            await delete_user_data(_TEST_TG_ID)

        async with factory() as session:
            row = (await session.execute(sa_select(SafetyEvent))).scalar_one()

        assert row.user_id is None            # was already NULL
        assert row.telegram_user_id is None   # must now also be NULL
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_has_consent_false_after_delete() -> None:
    """D-7: has_consent returns False after delete_user_data removes the user row."""
    engine, factory = await _make_test_db()
    try:
        async with factory() as session:
            session.add(_seed_user(_TEST_TG_ID))
            await session.commit()

        with patch("app.services.user_service.AsyncSessionLocal", factory):
            await delete_user_data(_TEST_TG_ID)
            result = await has_consent(_TEST_TG_ID)

        assert result is False  # D-7
    finally:
        await engine.dispose()
