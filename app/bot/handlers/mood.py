"""Mood diary handler."""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from app.bot.handlers.i18n import get_text, get_user_language
from app.services.user_service import save_mood_entry

logger = logging.getLogger(__name__)
router = Router()

# In-memory set of user IDs that clicked "Add a note" and haven't typed yet.
# Lost on restart — degraded to normal chat flow, which is acceptable.
_awaiting_note: set[int] = set()


def is_awaiting_note(user_id: int) -> bool:
    return user_id in _awaiting_note


def consume_note_waiter(user_id: int) -> None:
    _awaiting_note.discard(user_id)


@router.message(Command("mood"))
async def cmd_mood(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.5", lang), callback_data="mood_5"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.4", lang), callback_data="mood_4"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.3", lang), callback_data="mood_3"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.2", lang), callback_data="mood_2"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.1", lang), callback_data="mood_1"
                )
            ],
        ]
    )
    await message.answer(get_text("mood.question", lang), reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("mood_"))
async def on_mood_selected(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    mood = int(callback.data.split("_")[1])
    mood_label = get_text(f"mood.levels.{mood}", lang)

    try:
        await save_mood_entry(callback.from_user.id, mood)
        response_text = get_text("mood.saved", lang, mood=mood_label)
    except Exception:
        logger.exception("Failed to save mood entry for user %d", callback.from_user.id)
        response_text = get_text("chat.error", lang)

    await callback.message.edit_text(
        response_text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("mood.buttons.add_note", lang),
                        callback_data="add_mood_note",
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


@router.callback_query(lambda c: c.data == "add_mood_note")
async def on_mood_add_note(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    _awaiting_note.add(callback.from_user.id)
    await callback.message.edit_text(
        get_text("mood.add_note_prompt", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]
            ]
        ),
    )
    await callback.answer()
