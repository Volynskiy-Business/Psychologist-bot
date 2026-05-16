"""Interactive Safety Plan handler — section builder and full plan view."""

import logging

from aiogram import Router, types

from app.bot.handlers.i18n import get_text, get_user_language
from app.bot.user_state import clear_safety_section, set_safety_section
from app.db.models import SafetyPlanItem
from app.services.safety_plan_service import (
    SECTIONS,
    get_full_plan,
    get_items,
    get_section_counts,
)

logger = logging.getLogger(__name__)
router = Router()

_SECTION_NUMBERS = {
    "warning_signs": "1.",
    "coping_self": "2.",
    "distractions": "3.",
    "contacts": "4.",
    "professionals": "5.",
    "environment": "6.",
}


# ── Shared UI helpers ─────────────────────────────────────────────────────────


def _back_to_plan_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("safety_plan.buttons.back_to_plan", lang),
                    callback_data="safety_plan",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


def _section_keyboard(section: str, lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("safety_plan.buttons.add_item", lang),
                    callback_data=f"sp_add_{section}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("safety_plan.buttons.view_full", lang),
                    callback_data="sp_view_full",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("safety_plan.buttons.back_to_plan", lang),
                    callback_data="safety_plan",
                )
            ],
        ]
    )


def _build_section_text(
    items: list[SafetyPlanItem], section: str, lang: str
) -> str:
    num = _SECTION_NUMBERS.get(section, "")
    name = get_text(f"safety_plan.sections.{section}", lang)
    prompt = get_text(f"safety_plan.section_prompts.{section}", lang)
    lines = [f"{num} {name}\n\n{prompt}"]
    if items:
        lines.append("\n" + get_text("safety_plan.section_header", lang))
        for item in items:
            lines.append(f"• {item.content}")
    else:
        lines.append("\n" + get_text("safety_plan.section_empty_items", lang))
    return "\n".join(lines)


async def _show_section(
    callback: types.CallbackQuery, user_id: int, section: str, lang: str
) -> None:
    items = await get_items(user_id, section)
    text = _build_section_text(items, section, lang)
    await callback.message.edit_text(text, reply_markup=_section_keyboard(section, lang))
    await callback.answer()


async def send_section_view(
    message: types.Message, user_id: int, section: str, lang: str
) -> None:
    """Show updated section view via message.answer() — called from chat.py after item save."""
    items = await get_items(user_id, section)
    text = _build_section_text(items, section, lang)
    await message.answer(text, reply_markup=_section_keyboard(section, lang))


# ── Main Safety Plan menu ─────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "safety_plan")
async def on_safety_plan(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user_id = callback.from_user.id

    clear_safety_section(user_id)

    counts = await get_section_counts(user_id)

    def _section_btn(section: str) -> types.InlineKeyboardButton:
        num = _SECTION_NUMBERS.get(section, "")
        name = get_text(f"safety_plan.sections.{section}", lang)
        filled = "✅" if counts.get(section, 0) > 0 else "○"
        return types.InlineKeyboardButton(
            text=f"{filled} {num} {name}",
            callback_data=f"sp_section_{section}",
        )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [_section_btn("warning_signs")],
            [_section_btn("coping_self")],
            [_section_btn("distractions")],
            [_section_btn("contacts")],
            [_section_btn("professionals")],
            [_section_btn("environment")],
            [
                types.InlineKeyboardButton(
                    text=get_text("safety_plan.buttons.view_full", lang),
                    callback_data="sp_view_full",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )

    title = get_text("safety_plan.title", lang)
    intro = get_text("safety_plan.intro", lang)
    await callback.message.edit_text(
        f"{title}\n\n{intro}", reply_markup=keyboard
    )
    await callback.answer()


# ── Section view callbacks ────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data.startswith("sp_section_"))
async def on_section_view(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    section = callback.data[len("sp_section_"):]
    if section not in SECTIONS:
        await callback.answer()
        return
    await _show_section(callback, callback.from_user.id, section, lang)


# ── Add item flow ─────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data.startswith("sp_add_"))
async def on_section_add(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    section = callback.data[len("sp_add_"):]
    if section not in SECTIONS:
        await callback.answer()
        return
    user_id = callback.from_user.id
    set_safety_section(user_id, section)
    prompt = get_text("safety_plan.add_item_prompt", lang)
    await callback.message.edit_text(
        prompt,
        reply_markup=_back_to_plan_keyboard(lang),
    )
    await callback.answer()


# ── Full plan view ────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "sp_view_full")
async def on_view_full_plan(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user_id = callback.from_user.id
    plan = await get_full_plan(user_id)

    title = get_text("safety_plan.full_plan_title", lang)
    not_filled = get_text("safety_plan.not_filled", lang)

    has_any = any(items for items in plan.values())
    if not has_any:
        text = f"{title}\n\n{get_text('safety_plan.full_plan_empty', lang)}"
    else:
        lines = [title]
        for section in SECTIONS:
            num = _SECTION_NUMBERS.get(section, "")
            name = get_text(f"safety_plan.sections.{section}", lang)
            lines.append(f"\n{num} {name}")
            items = plan.get(section, [])
            if items:
                for item in items:
                    lines.append(f"• {item.content}")
            else:
                lines.append(not_filled)
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("safety_plan.buttons.back_to_plan", lang),
                        callback_data="safety_plan",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ],
            ]
        ),
    )
    await callback.answer()
