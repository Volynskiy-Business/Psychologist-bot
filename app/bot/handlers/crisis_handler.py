"""Crisis lock callback handlers — active during Tier 4 (imminent risk) state."""

import logging

from aiogram import Router, types

from app.bot.handlers.i18n import get_text, get_user_language
from app.bot.user_state import clear_crisis_lock

logger = logging.getLogger(__name__)
router = Router()


def crisis_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Three-button keyboard shown during Tier 4 crisis state."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("crisis.tier4_btn_1", lang),
                callback_data="crisis_1",
            )],
            [types.InlineKeyboardButton(
                text=get_text("crisis.tier4_btn_2", lang),
                callback_data="crisis_2",
            )],
            [types.InlineKeyboardButton(
                text=get_text("crisis.tier4_btn_3", lang),
                callback_data="crisis_3",
            )],
        ]
    )


@router.callback_query(lambda c: c.data == "crisis_1")
async def crisis_btn_danger(callback: types.CallbackQuery) -> None:
    """User reports they are in immediate danger — re-escalate with emergency guidance."""
    lang = get_user_language(callback.from_user)
    await callback.answer()
    await callback.message.answer(
        get_text("crisis.tier4_btn1_response", lang),
        reply_markup=crisis_keyboard(lang),
    )
    logger.info("stage=crisis_lock action=btn1_danger")


@router.callback_query(lambda c: c.data == "crisis_2")
async def crisis_btn_safe(callback: types.CallbackQuery) -> None:
    """User reports they moved away from danger — acknowledge and release lock."""
    lang = get_user_language(callback.from_user)
    await callback.answer()
    clear_crisis_lock(callback.from_user.id)
    await callback.message.answer(get_text("crisis.tier4_btn2_response", lang))
    logger.info("stage=crisis_lock action=btn2_safe lock=released")


@router.callback_query(lambda c: c.data == "crisis_3")
async def crisis_btn_contacted(callback: types.CallbackQuery) -> None:
    """User reports they contacted someone — acknowledge and release lock."""
    lang = get_user_language(callback.from_user)
    await callback.answer()
    clear_crisis_lock(callback.from_user.id)
    await callback.message.answer(get_text("crisis.tier4_btn3_response", lang))
    logger.info("stage=crisis_lock action=btn3_contacted lock=released")
