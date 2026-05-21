"""Reply keyboard shown after each AI response — back-to-menu only."""

import logging

from aiogram import Router, types

from app.bot.handlers.i18n import get_text, get_user_language

logger = logging.getLogger(__name__)
router = Router()


def feedback_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Return a simple back-to-menu keyboard (feedback thumbs removed)."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


# Keep handlers alive so old cached messages with fbk_y/fbk_n buttons don't crash
@router.callback_query(lambda c: c.data in ("fbk_y", "fbk_n"))
async def on_feedback(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_reply_markup(
        reply_markup=feedback_keyboard(lang)
    )
    await callback.answer()
