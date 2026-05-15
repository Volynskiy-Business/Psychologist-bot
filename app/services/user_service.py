import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message, MoodEntry, RiskLevel, SafetyEvent, User
from app.db.session import AsyncSessionLocal


class DeleteUserDataResult(enum.Enum):
    DELETED = "deleted"
    NOT_FOUND = "not_found"


async def upsert_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    language: str = "ru",
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language=language,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(user)
        await session.flush()
    else:
        user.username = username
        user.first_name = first_name
        user.language = language
        user.updated_at = datetime.utcnow()
    return user


async def grant_consent(
    *,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    language: str = "ru",
) -> None:
    async with AsyncSessionLocal() as session:
        user = await upsert_user(
            session,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language=language,
        )
        user.consent_given = True
        if user.consent_accepted_at is None:  # preserve first acceptance timestamp
            user.consent_accepted_at = datetime.utcnow()
        await session.commit()


async def has_consent(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.consent_given).where(User.telegram_id == telegram_id)
        )
        return bool(result.scalar_one_or_none())


async def save_mood_entry(telegram_id: int, mood_score: int) -> None:
    async with AsyncSessionLocal() as session:
        user = await upsert_user(session, telegram_id=telegram_id)
        entry = MoodEntry(
            user_id=user.id,
            mood_score=mood_score,
            anxiety_score=5,
            energy_score=5,
            created_at=datetime.utcnow(),
        )
        session.add(entry)
        await session.commit()


async def record_safety_event(
    *,
    telegram_user_id: int,
    risk_level: RiskLevel,
    matched_pattern: Optional[str],
) -> None:
    async with AsyncSessionLocal() as session:
        event = SafetyEvent(
            telegram_user_id=telegram_user_id,
            risk_level=risk_level,
            risk_type="deterministic_keyword",
            confidence=1.0,
            reason=matched_pattern or "",
            requires_crisis_response=True,
            requires_professional_referral=(risk_level >= RiskLevel.IMMINENT_RISK),
            created_at=datetime.utcnow(),
        )
        session.add(event)
        await session.commit()


async def delete_user_data(telegram_user_id: int) -> DeleteUserDataResult:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return DeleteUserDataResult.NOT_FOUND

        user_id = user.id

        await session.execute(delete(MoodEntry).where(MoodEntry.user_id == user_id))
        await session.execute(delete(Message).where(Message.user_id == user_id))

        # Nullify both FK and direct Telegram identifier on retained audit rows.
        # Covers post-consent rows (user_id set via FK) and pre-consent rows
        # (user_id NULL, telegram_user_id set).  Rows are kept for anonymised
        # crisis audit; no direct identifier survives deletion.
        await session.execute(
            update(SafetyEvent)
            .where(
                or_(
                    SafetyEvent.user_id == user_id,
                    SafetyEvent.telegram_user_id == telegram_user_id,
                )
            )
            .values(user_id=None, telegram_user_id=None)
        )

        await session.delete(user)
        await session.commit()

        return DeleteUserDataResult.DELETED
