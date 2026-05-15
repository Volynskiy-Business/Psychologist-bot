"""Exercises sub-menu handler — breathing, CBT thought record, mindfulness."""

from aiogram import Router, types

from app.bot.handlers.i18n import get_text, get_user_language

router = Router()


def _back_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("menu.back_to_menu", lang),
                callback_data="back_to_menu",
            )]
        ]
    )


@router.callback_query(lambda c: c.data == "mode_exercises")
async def on_exercises_menu(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("exercises.buttons.breathing", lang),
                callback_data="ex_breathing",
            )],
            [types.InlineKeyboardButton(
                text=get_text("exercises.buttons.cbt", lang),
                callback_data="ex_cbt",
            )],
            [types.InlineKeyboardButton(
                text=get_text("exercises.buttons.mindfulness", lang),
                callback_data="ex_mindfulness",
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.back_to_menu", lang),
                callback_data="back_to_menu",
            )],
        ]
    )
    await callback.message.edit_text(
        get_text("exercises.title", lang),
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "ex_breathing")
async def on_exercise_breathing(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("exercises.breathing", lang),
        reply_markup=_back_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "ex_cbt")
async def on_exercise_cbt(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("exercises.cbt", lang),
        reply_markup=_back_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "ex_mindfulness")
async def on_exercise_mindfulness(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("exercises.mindfulness", lang),
        reply_markup=_back_keyboard(lang),
    )
    await callback.answer()
