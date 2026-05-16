"""Safety plan persistence service."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import SafetyPlan, SafetyPlanItem, User
from app.db.session import AsyncSessionLocal

SECTIONS = [
    "warning_signs",
    "coping_self",
    "distractions",
    "contacts",
    "professionals",
    "environment",
]


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_or_create_plan(session, user_id: int) -> SafetyPlan:
    result = await session.execute(
        select(SafetyPlan).where(SafetyPlan.user_id == user_id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        now = _utc_now_naive()
        plan = SafetyPlan(user_id=user_id, created_at=now, updated_at=now)
        session.add(plan)
        await session.flush()
    return plan


async def _resolve_user_id(session, telegram_id: int) -> int | None:
    result = await session.execute(
        select(User.id).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def add_item(telegram_id: int, section: str, content: str) -> SafetyPlanItem:
    async with AsyncSessionLocal() as session:
        user_id = await _resolve_user_id(session, telegram_id)
        if user_id is None:
            raise ValueError("User not found")
        plan = await _get_or_create_plan(session, user_id)
        result = await session.execute(
            select(SafetyPlanItem)
            .where(SafetyPlanItem.plan_id == plan.id)
            .where(SafetyPlanItem.section == section)
            .order_by(SafetyPlanItem.position.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        position = (last.position + 1) if last else 0
        item = SafetyPlanItem(
            plan_id=plan.id,
            section=section,
            content=content,
            position=position,
            created_at=_utc_now_naive(),
        )
        session.add(item)
        plan.updated_at = _utc_now_naive()
        await session.commit()
        await session.refresh(item)
        return item


async def get_items(telegram_id: int, section: str) -> list[SafetyPlanItem]:
    async with AsyncSessionLocal() as session:
        user_id = await _resolve_user_id(session, telegram_id)
        if user_id is None:
            return []
        result = await session.execute(
            select(SafetyPlan).where(SafetyPlan.user_id == user_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return []
        result = await session.execute(
            select(SafetyPlanItem)
            .where(SafetyPlanItem.plan_id == plan.id)
            .where(SafetyPlanItem.section == section)
            .order_by(SafetyPlanItem.position)
        )
        return list(result.scalars().all())


async def get_full_plan(telegram_id: int) -> dict[str, list[SafetyPlanItem]]:
    async with AsyncSessionLocal() as session:
        user_id = await _resolve_user_id(session, telegram_id)
        if user_id is None:
            return {s: [] for s in SECTIONS}
        result = await session.execute(
            select(SafetyPlan).where(SafetyPlan.user_id == user_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return {s: [] for s in SECTIONS}
        result = await session.execute(
            select(SafetyPlanItem)
            .where(SafetyPlanItem.plan_id == plan.id)
            .order_by(SafetyPlanItem.section, SafetyPlanItem.position)
        )
        items = result.scalars().all()
        by_section: dict[str, list[SafetyPlanItem]] = {s: [] for s in SECTIONS}
        for item in items:
            if item.section in by_section:
                by_section[item.section].append(item)
        return by_section


async def get_section_counts(telegram_id: int) -> dict[str, int]:
    """Return item counts per section for building the main menu."""
    async with AsyncSessionLocal() as session:
        user_id = await _resolve_user_id(session, telegram_id)
        if user_id is None:
            return {s: 0 for s in SECTIONS}
        result = await session.execute(
            select(SafetyPlan).where(SafetyPlan.user_id == user_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return {s: 0 for s in SECTIONS}
        result = await session.execute(
            select(SafetyPlanItem).where(SafetyPlanItem.plan_id == plan.id)
        )
        items = result.scalars().all()
        counts: dict[str, int] = {s: 0 for s in SECTIONS}
        for item in items:
            if item.section in counts:
                counts[item.section] += 1
        return counts


async def delete_plan_data(telegram_id: int) -> None:
    """Remove all safety plan data for a user — called by delete_user_data."""
    async with AsyncSessionLocal() as session:
        user_id = await _resolve_user_id(session, telegram_id)
        if user_id is None:
            return
        result = await session.execute(
            select(SafetyPlan).where(SafetyPlan.user_id == user_id)
        )
        plan = result.scalar_one_or_none()
        if plan is not None:
            await session.delete(plan)
            await session.commit()
