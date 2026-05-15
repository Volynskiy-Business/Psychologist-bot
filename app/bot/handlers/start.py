"""Start handler with consent flow and main menu callbacks."""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from app.bot.handlers.i18n import get_text, get_user_language, load_translation
from app.services.user_service import DeleteUserDataResult, delete_user_data, grant_consent, has_consent

logger = logging.getLogger(__name__)

router = Router()


def _back_to_menu_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=get_text("menu.back_to_menu", lang),
                callback_data="back_to_menu",
            )
        ]]
    )


def _start_content(lang: str) -> tuple[str, types.InlineKeyboardMarkup]:
    """Return (text, keyboard) for the /start consent screen."""
    text = (
        f"{get_text('start.greeting', lang)}\n\n"
        f"{get_text('start.capabilities', lang)}\n\n"
        f"{get_text('start.disclaimer', lang)}\n\n"
        f"{get_text('start.crisis_warning', lang)}\n\n"
        f"{get_text('start.consent', lang)}"
    )
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("start.buttons.continue", lang),
                callback_data="consent_agree",
            )],
            [types.InlineKeyboardButton(
                text=get_text("start.buttons.crisis", lang),
                callback_data="crisis_help",
            )],
            [types.InlineKeyboardButton(
                text=get_text("start.buttons.privacy", lang),
                callback_data="privacy_policy",
            )],
        ]
    )
    return text, keyboard


def main_menu_keyboard(lang: str = "en") -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("menu.chat", lang), callback_data="mode_chat"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.anxiety", lang), callback_data="mode_anxiety"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.sad", lang), callback_data="mode_sad"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.mood", lang), callback_data="mode_mood"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.exercises", lang), callback_data="mode_exercises"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.safety_plan", lang), callback_data="safety_plan"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.settings", lang), callback_data="settings"
            )],
        ]
    )


# ── /start command ────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    if await has_consent(message.from_user.id):
        await message.answer(get_text("start.thanks", lang), reply_markup=main_menu_keyboard(lang))
        return
    text, keyboard = _start_content(lang)
    await message.answer(text, reply_markup=keyboard)


# ── Consent screen callbacks ──────────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "consent_agree")
async def on_consent_agree(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await grant_consent(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language=lang,
    )
    await callback.message.edit_text(
        get_text("start.thanks", lang),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "crisis_help")
async def on_crisis_help(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        "🆘 " + get_text("crisis.response", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text=get_text("menu.back", lang),
                    callback_data="back_to_start",
                )
            ]]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "privacy_policy")
async def on_privacy_policy(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("privacy.policy", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text=get_text("menu.back", lang),
                    callback_data="back_to_start",
                )
            ]]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_start")
async def on_back_to_start(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    text, keyboard = _start_content(lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ── Main menu navigation ──────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "back_to_menu")
async def on_back_to_menu(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("start.thanks", lang),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


# ── Chat / support mode intros ────────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "mode_chat")
async def on_mode_chat(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("modes.chat_intro", lang),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_anxiety")
async def on_mode_anxiety(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("modes.anxiety_intro", lang),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_sad")
async def on_mode_sad(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("modes.sad_intro", lang),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


# ── Mood diary from menu ──────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "mode_mood")
async def on_mode_mood(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=get_text("mood.levels.5", lang), callback_data="mood_5"
            )],
            [types.InlineKeyboardButton(
                text=get_text("mood.levels.4", lang), callback_data="mood_4"
            )],
            [types.InlineKeyboardButton(
                text=get_text("mood.levels.3", lang), callback_data="mood_3"
            )],
            [types.InlineKeyboardButton(
                text=get_text("mood.levels.2", lang), callback_data="mood_2"
            )],
            [types.InlineKeyboardButton(
                text=get_text("mood.levels.1", lang), callback_data="mood_1"
            )],
            [types.InlineKeyboardButton(
                text=get_text("menu.back_to_menu", lang),
                callback_data="back_to_menu",
            )],
        ]
    )
    await callback.message.edit_text(
        get_text("mood.question", lang),
        reply_markup=keyboard,
    )
    await callback.answer()


# ── Safety plan ───────────────────────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "safety_plan")
async def on_safety_plan(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    t = load_translation(lang)
    items: list[str] = t.get("safety_plan", {}).get("items", [])
    text = (
        get_text("safety_plan.title", lang)
        + "\n\n"
        + "\n".join(items)
        + "\n\n"
        + get_text("safety_plan.start_filling", lang)
    )
    await callback.message.edit_text(
        text,
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


# ── Settings ──────────────────────────────────────────────────────────────────

_LANG_DISPLAY = {
    "ru": "Русский 🇷🇺",
    "en": "English 🇬🇧",
    "de": "Deutsch 🇩🇪",
    "fr": "Français 🇫🇷",
    "no": "Norsk 🇳🇴",
    "da": "Dansk 🇩🇰",
    "pt": "Português 🇵🇹",
}


@router.callback_query(lambda c: c.data == "settings")
async def on_settings(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    lang_name = _LANG_DISPLAY.get(lang, "English 🇬🇧")
    text = (
        get_text("settings.title", lang)
        + "\n\n"
        + get_text("settings.language", lang)
        + ": "
        + lang_name
    )
    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=get_text("settings.delete_data", lang),
                    callback_data="delete_my_data",
                )],
                [types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "delete_my_data")
async def on_delete_my_data(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("privacy.delete_confirm", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=get_text("settings.confirm_delete", lang),
                    callback_data="delete_confirmed",
                )],
                [types.InlineKeyboardButton(
                    text=get_text("menu.back", lang),
                    callback_data="back_to_menu",
                )],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "delete_confirmed")
async def on_delete_confirmed(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    try:
        result = await delete_user_data(callback.from_user.id)
    except Exception:
        logger.exception("Failed to delete data for user %d", callback.from_user.id)
        await callback.message.edit_text(
            get_text("chat.error", lang),
            reply_markup=_back_to_menu_keyboard(lang),
        )
        await callback.answer()
        return

    if result == DeleteUserDataResult.NOT_FOUND:
        text = get_text("privacy.not_found", lang)
    else:
        text = get_text("privacy.deleted", lang)

    await callback.message.edit_text(text, reply_markup=_back_to_menu_keyboard(lang))
    await callback.answer()
