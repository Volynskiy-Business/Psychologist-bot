"""Thumbs-up / thumbs-down feedback on support responses."""

import logging

from aiogram import Router, types

from app.bot.handlers.i18n import get_text, get_user_language
from app.services.feedback_service import record_response_feedback

logger = logging.getLogger(__name__)
router = Router()


def feedback_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Keyboard with feedback buttons appended below back-to-menu."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("feedback.helpful", lang),
                    callback_data="fbk_y",
                ),
                types.InlineKeyboardButton(
                    text=get_text("feedback.not_helpful", lang),
                    callback_data="fbk_n",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


def _back_only_kb(lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ]
        ]
    )


@router.callback_query(lambda c: c.data in ("fbk_y", "fbk_n"))
async def on_feedback(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    helpful = callback.data == "fbk_y"
    try:
        await record_response_feedback(callback.from_user.id, helpful)
    except Exception:
        logger.exception("on_feedback: failed to record")
    await callback.message.edit_reply_markup(reply_markup=_back_only_kb(lang))
    await callback.answer(get_text("feedback.thanks", lang))
