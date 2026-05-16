"""Tests for Safety Plan handler and service (SP-1 to SP-9)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, User
from app.services.safety_plan_service import SECTIONS


# ── Shared helpers ────────────────────────────────────────────────────────────

def _utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_user(tg_id: int, pk: int = 1) -> User:
    # SQLite renders BigInteger PKs as BIGINT NOT NULL + separate PRIMARY KEY(id),
    # which breaks rowid-alias autoincrement. Set id explicitly for in-memory tests.
    return User(
        id=pk,
        telegram_id=tg_id,
        language="en",
        consent_given=True,
        consent_accepted_at=_utc_naive(),
        created_at=_utc_naive(),
        updated_at=_utc_naive(),
    )


def _make_callback(data: str, user_id: int = 1001, lang: str = "en") -> MagicMock:
    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = lang

    callback = MagicMock()
    callback.data = data
    callback.from_user = from_user
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


async def _make_test_db():
    """In-memory SQLite DB with full schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    return engine, factory


# ── SP-1: Main safety plan menu has interactive section buttons ───────────────

@pytest.mark.asyncio
async def test_safety_plan_main_menu_renders_section_buttons() -> None:
    """SP-1: on_safety_plan callback renders a keyboard with all 6 section buttons."""
    from app.bot.handlers.safety_plan import on_safety_plan

    callback = _make_callback("safety_plan", user_id=1001)

    mock_counts = AsyncMock(return_value={s: 0 for s in SECTIONS})
    with patch("app.bot.handlers.safety_plan.get_section_counts", mock_counts):
        await on_safety_plan(callback)

    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()

    call_kwargs = callback.message.edit_text.call_args
    keyboard = call_kwargs.kwargs.get("reply_markup") or call_kwargs.args[1]
    button_datas = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
    ]
    for section in SECTIONS:
        assert f"sp_section_{section}" in button_datas, f"Missing button for {section}"


# ── SP-2: Tapping a section shows that section's view ────────────────────────

@pytest.mark.asyncio
async def test_section_view_shows_section_content() -> None:
    """SP-2: sp_section_warning_signs renders section title and add-item button."""
    from app.bot.handlers.safety_plan import on_section_view

    callback = _make_callback("sp_section_warning_signs", user_id=1002)

    mock_items = AsyncMock(return_value=[])
    with patch("app.bot.handlers.safety_plan.get_items", mock_items):
        await on_section_view(callback)

    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()

    text = callback.message.edit_text.call_args.args[0]
    assert "warning" in text.lower() or "sign" in text.lower()

    keyboard = callback.message.edit_text.call_args.kwargs.get("reply_markup") or \
               callback.message.edit_text.call_args.args[1]
    datas = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "sp_add_warning_signs" in datas


# ── SP-3: Add item callback sets safety section state ────────────────────────

@pytest.mark.asyncio
async def test_add_item_sets_safety_section_state() -> None:
    """SP-3: sp_add_warning_signs sets user_state safety_section and shows input prompt."""
    import app.bot.user_state as user_state
    from app.bot.handlers.safety_plan import on_section_add

    user_id = 1003
    user_state.clear_safety_section(user_id)

    callback = _make_callback("sp_add_warning_signs", user_id=user_id)

    await on_section_add(callback)

    assert user_state.get_safety_section(user_id) == "warning_signs"
    callback.message.edit_text.assert_called_once()
    callback.answer.assert_called_once()
    prompt_text = callback.message.edit_text.call_args.args[0]
    assert len(prompt_text) > 0

    user_state.clear_safety_section(user_id)  # cleanup


# ── SP-4: Full plan view shows empty state when no items saved ────────────────

@pytest.mark.asyncio
async def test_full_plan_view_empty_state() -> None:
    """SP-4: sp_view_full shows empty plan message when no items exist."""
    from app.bot.handlers.safety_plan import on_view_full_plan

    callback = _make_callback("sp_view_full", user_id=1004)

    empty_plan = {s: [] for s in SECTIONS}
    mock_plan = AsyncMock(return_value=empty_plan)
    with patch("app.bot.handlers.safety_plan.get_full_plan", mock_plan):
        await on_view_full_plan(callback)

    callback.message.edit_text.assert_called_once()
    text = callback.message.edit_text.call_args.args[0]
    assert "empty" in text.lower() or "tap" in text.lower() or "пуст" in text.lower()


# ── SP-5: Chat handler saves item to active safety section ────────────────────

@pytest.mark.asyncio
async def test_chat_handler_saves_safety_plan_item() -> None:
    """SP-5: when safety section is active, handle_message saves item and shows section view."""
    import app.bot.user_state as user_state
    from app.bot.handlers.chat import handle_message

    user_id = 1005
    user_state.set_safety_section(user_id, "coping_self")

    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = "en"

    msg = MagicMock()
    msg.text = "Go for a walk when I feel overwhelmed"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()

    mock_add = AsyncMock()
    mock_section_view = AsyncMock()

    with (
        patch("app.bot.handlers.chat.deterministic_crisis_check", return_value=(0, None)),
        patch("app.bot.handlers.chat.has_consent", new_callable=AsyncMock, return_value=True),
        patch("app.bot.handlers.chat.add_safety_plan_item", mock_add),
        patch("app.bot.handlers.chat.send_section_view", mock_section_view),
        patch("app.bot.handlers.chat.OpenRouterClient") as mock_client_cls,
    ):
        await handle_message(msg)

    mock_add.assert_called_once_with(
        user_id, "coping_self", "Go for a walk when I feel overwhelmed"
    )
    mock_section_view.assert_called_once_with(msg, user_id, "coping_self", "en")
    mock_client_cls.assert_not_called()
    assert user_state.get_safety_section(user_id) is None


# ── SP-6: Crisis phrase during safety plan editing is intercepted ─────────────

@pytest.mark.asyncio
async def test_crisis_phrase_intercepted_before_safety_plan_save() -> None:
    """SP-6: crisis phrase during section editing triggers crisis response, not item save."""
    import app.bot.user_state as user_state
    from app.db.models import RiskLevel
    from app.bot.handlers.chat import handle_message

    user_id = 1006
    user_state.set_safety_section(user_id, "warning_signs")

    from_user = MagicMock()
    from_user.id = user_id
    from_user.language_code = "ru"

    msg = MagicMock()
    msg.text = "жить не хочется"
    msg.from_user = from_user
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.bot = MagicMock()

    mock_add = AsyncMock()
    crisis_level = RiskLevel.ELEVATED_DISTRESS

    with (
        patch(
            "app.bot.handlers.chat.deterministic_crisis_check",
            return_value=(crisis_level, "жить не хочется"),
        ),
        patch("app.bot.handlers.chat.record_safety_event", new_callable=AsyncMock),
        patch("app.bot.handlers.chat.add_safety_plan_item", mock_add),
        patch("app.bot.handlers.chat.get_crisis_response", return_value="crisis msg"),
    ):
        await handle_message(msg)

    mock_add.assert_not_called()
    msg.answer.assert_called_once_with("crisis msg")
    assert user_state.get_safety_section(user_id) is None


# ── SP-7: Back to menu clears safety section state ───────────────────────────

@pytest.mark.asyncio
async def test_back_to_menu_clears_safety_section() -> None:
    """SP-7: on_back_to_menu callback clears the safety section editing state."""
    import app.bot.user_state as user_state
    from app.bot.handlers.start import on_back_to_menu

    user_id = 1007
    user_state.set_safety_section(user_id, "contacts")

    callback = _make_callback("back_to_menu", user_id=user_id)

    await on_back_to_menu(callback)

    assert user_state.get_safety_section(user_id) is None
    callback.message.edit_text.assert_called_once()


# ── SP-8: Safety plan service — add, get, full plan (SQLite) ─────────────────

@pytest.mark.asyncio
async def test_safety_plan_service_add_and_get_items() -> None:
    """SP-8a: add_item persists an item; get_items retrieves it by section."""
    from app.services.safety_plan_service import add_item, get_items

    engine, factory = await _make_test_db()

    async with factory() as session:
        session.add(_seed_user(9001, pk=1))
        await session.commit()

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        item = await add_item(9001, "contacts", "My therapist — 555-0100")

    assert item.content == "My therapist — 555-0100"
    assert item.section == "contacts"
    assert item.position == 0

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        items = await get_items(9001, "contacts")

    assert len(items) == 1
    assert items[0].content == "My therapist — 555-0100"

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        other = await get_items(9001, "warning_signs")
    assert other == []

    await engine.dispose()


@pytest.mark.asyncio
async def test_safety_plan_service_full_plan() -> None:
    """SP-8b: get_full_plan returns items grouped by section; empty sections return []."""
    from app.services.safety_plan_service import add_item, get_full_plan

    engine, factory = await _make_test_db()

    async with factory() as session:
        session.add(_seed_user(9002, pk=1))
        await session.commit()

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        await add_item(9002, "warning_signs", "I stop sleeping")
        await add_item(9002, "warning_signs", "I withdraw from friends")

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        plan = await get_full_plan(9002)

    assert len(plan["warning_signs"]) == 2
    assert plan["coping_self"] == []
    assert set(plan.keys()) == set(SECTIONS)

    await engine.dispose()


@pytest.mark.asyncio
async def test_safety_plan_service_delete_plan_data() -> None:
    """SP-8c: delete_plan_data removes all items and the plan for a user."""
    from app.services.safety_plan_service import add_item, delete_plan_data, get_full_plan

    engine, factory = await _make_test_db()

    async with factory() as session:
        session.add(_seed_user(9003, pk=1))
        await session.commit()

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        await add_item(9003, "contacts", "Friend A")

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        await delete_plan_data(9003)

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        plan = await get_full_plan(9003)

    assert all(items == [] for items in plan.values())

    await engine.dispose()


# ── SP-9: delete_my_data removes safety plan data ────────────────────────────

@pytest.mark.asyncio
async def test_delete_my_data_removes_safety_plan() -> None:
    """SP-9: delete_user_data deletes the user's safety plan rows."""
    from app.services.safety_plan_service import add_item, get_full_plan
    from app.services.user_service import DeleteUserDataResult, delete_user_data

    engine, factory = await _make_test_db()

    # Seed user with explicit PK (SQLite BigInteger PK workaround).
    async with factory() as session:
        session.add(_seed_user(9004, pk=1))
        await session.commit()

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        await add_item(9004, "coping_self", "Deep breathing")

    # delete_user_data operates in its own session; point it at the same factory.
    with patch("app.services.user_service.AsyncSessionLocal", factory):
        result = await delete_user_data(9004)

    assert result == DeleteUserDataResult.DELETED

    with patch("app.services.safety_plan_service.AsyncSessionLocal", factory):
        plan = await get_full_plan(9004)

    assert all(items == [] for items in plan.values())

    await engine.dispose()
