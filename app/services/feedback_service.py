"""Record user feedback on bot responses."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Feedback, User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def record_response_feedback(telegram_user_id: int, helpful: bool) -> None:
    """Store a thumbs-up/down rating for a support response."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_user_id)
        )
        user_id = result.scalar_one_or_none()
        if user_id is None:
            logger.warning("record_feedback: user not found for id=REDACTED")
            return
        fb = Feedback(
            user_id=user_id,
            rating=1 if helpful else 0,
            created_at=_utc_now_naive(),
        )
        session.add(fb)
        await session.commit()
