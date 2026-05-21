"""Start handler with consent flow, onboarding, and main menu callbacks."""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from app.ai.agents.onboarding_agent import OnboardingAgent, get_consultant_names
from app.ai.openrouter_client import OpenRouterClient
from app.bot.handlers.i18n import get_text, get_user_language
from app.bot.user_state import (
    MODE_ANXIETY_SUPPORT,
    MODE_FRIENDLY_CHAT,
    MODE_SADNESS_SUPPORT,
    clear_mode,
    clear_onboarding_step,
    clear_safety_section,
    get_onboarding_step,
    set_mode,
    set_onboarding_step,
)
from app.config import settings
from app.services.user_service import (
    DeleteUserDataResult,
    delete_user_data,
    get_user_by_telegram_id,
    grant_consent,
    has_consent,
    update_user_profile,
)

logger = logging.getLogger(__name__)

router = Router()


def _back_to_menu_keyboard(lang: str) -> types.InlineKeyboardMarkup:
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
            [
                types.InlineKeyboardButton(
                    text=get_text("start.buttons.continue", lang),
                    callback_data="consent_agree",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("start.buttons.crisis", lang),
                    callback_data="crisis_help",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("start.buttons.privacy", lang),
                    callback_data="privacy_policy",
                )
            ],
        ]
    )
    return text, keyboard


def main_menu_keyboard(lang: str = "en") -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.chat", lang), callback_data="mode_chat"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.anxiety", lang), callback_data="mode_anxiety"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.sad", lang), callback_data="mode_sad"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.mood", lang), callback_data="mode_mood"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.exercises", lang),
                    callback_data="mode_exercises",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.safety_plan", lang), callback_data="safety_plan"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.settings", lang), callback_data="settings"
                )
            ],
        ]
    )


# ── /start command ────────────────────────────────────────────────────────────


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    if await has_consent(message.from_user.id):
        user = await get_user_by_telegram_id(message.from_user.id)
        if user and user.onboarding_completed:
            await message.answer(
                get_text("start.thanks", lang), reply_markup=main_menu_keyboard(lang)
            )
        else:
            # Consent given but onboarding not done — restart onboarding
            await _launch_onboarding(message.from_user.id, lang, message)
        return
    text, keyboard = _start_content(lang)
    await message.answer(text, reply_markup=keyboard)


async def _launch_onboarding(
    telegram_id: int,
    lang: str,
    message: types.Message,
) -> None:
    """Start onboarding: send first warm greeting and set step=1."""
    client = OpenRouterClient()
    try:
        female_name, male_name = get_consultant_names(None, lang)
        agent = OnboardingAgent(client, model=settings.default_model)
        greeting = await agent.start_message(lang, female_name, male_name, "female")
        set_onboarding_step(telegram_id, 1)
        await message.answer(greeting)
    except Exception:
        logger.exception("_launch_onboarding failed; skipping to main menu")
        set_onboarding_step(telegram_id, 0)
        await message.answer(
            get_text("start.thanks", lang), reply_markup=main_menu_keyboard(lang)
        )
    finally:
        await client.close()


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
    await callback.answer()

    # Launch onboarding conversation
    client = OpenRouterClient()
    try:
        female_name, male_name = get_consultant_names(None, lang)
        agent = OnboardingAgent(client, model=settings.default_model)
        greeting = await agent.start_message(lang, female_name, male_name, "female")
        set_onboarding_step(callback.from_user.id, 1)
        # Edit the consent message away and send the onboarding greeting
        await callback.message.edit_text(greeting)
    except Exception:
        logger.exception("on_consent_agree onboarding failed; skipping to main menu")
        set_onboarding_step(callback.from_user.id, 0)
        await callback.message.edit_text(
            get_text("start.thanks", lang),
            reply_markup=main_menu_keyboard(lang),
        )
    finally:
        await client.close()


@router.callback_query(lambda c: c.data == "crisis_help")
async def on_crisis_help(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        "🆘 " + get_text("crisis.response", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back", lang),
                        callback_data="back_to_start",
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "privacy_policy")
async def on_privacy_policy(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("privacy.policy", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back", lang),
                        callback_data="back_to_start",
                    )
                ]
            ]
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
    clear_mode(callback.from_user.id)
    clear_safety_section(callback.from_user.id)
    clear_onboarding_step(callback.from_user.id)
    await callback.message.edit_text(
        get_text("start.thanks", lang),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


# ── Chat / support mode intros ────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "mode_chat")
async def on_mode_chat(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    set_mode(callback.from_user.id, MODE_FRIENDLY_CHAT)
    await callback.message.edit_text(
        get_text("modes.chat_intro", lang),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_anxiety")
async def on_mode_anxiety(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    set_mode(callback.from_user.id, MODE_ANXIETY_SUPPORT)
    await callback.message.edit_text(
        get_text("modes.anxiety_intro", lang),
        reply_markup=_back_to_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "mode_sad")
async def on_mode_sad(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    set_mode(callback.from_user.id, MODE_SADNESS_SUPPORT)
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
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )
    await callback.message.edit_text(
        get_text("mood.question", lang),
        reply_markup=keyboard,
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
    "es": "Español 🇪🇸",
}

_GENDER_DISPLAY = {
    "male": "Мужской 👨",
    "female": "Женский 👩",
    "other": "Другой 👤",
}


@router.callback_query(lambda c: c.data == "settings")
async def on_settings(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user = await get_user_by_telegram_id(callback.from_user.id)

    lang_name = _LANG_DISPLAY.get(lang, "English 🇬🇧")

    # Build profile display
    if user:
        c_gender = getattr(user, "consultant_gender", "female")
        female_name, male_name = get_consultant_names(
            getattr(user, "region", None), lang
        )
        consultant_display = (
            f"{male_name} 👨‍⚕️" if c_gender == "male" else f"{female_name} 👩‍⚕️"
        )
        u_gender_display = _GENDER_DISPLAY.get(
            getattr(user, "gender", None) or "", get_text("settings.gender_unknown", lang)
        )
        country_display = getattr(user, "region", None) or get_text("settings.not_set", lang)

        text = (
            f"{get_text('settings.title', lang)}\n\n"
            f"🌐 {get_text('settings.language', lang)}: {lang_name}\n"
            f"👥 {get_text('settings.consultant_label', lang)}: {consultant_display}\n"
            f"👤 {get_text('settings.user_gender_label', lang)}: {u_gender_display}\n"
            f"🌎 {get_text('settings.country_label', lang)}: {country_display}"
        )

        # Toggle button: show the OTHER consultant option
        if c_gender == "male":
            toggle_text = f"🔄 {get_text('settings.switch_to_female', lang)} ({female_name} 👩‍⚕️)"
            toggle_cb = "consultant_switch_female"
        else:
            toggle_text = f"🔄 {get_text('settings.switch_to_male', lang)} ({male_name} 👨‍⚕️)"
            toggle_cb = "consultant_switch_male"
    else:
        text = f"{get_text('settings.title', lang)}\n\n🌐 {get_text('settings.language', lang)}: {lang_name}"
        toggle_text = ""
        toggle_cb = ""

    keyboard_rows = []
    if toggle_text:
        keyboard_rows.append([
            types.InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)
        ])
    keyboard_rows.append([
        types.InlineKeyboardButton(
            text=get_text("settings.edit_profile", lang),
            callback_data="redo_onboarding",
        )
    ])
    keyboard_rows.append([
        types.InlineKeyboardButton(
            text=get_text("settings.delete_data", lang),
            callback_data="delete_my_data",
        )
    ])
    keyboard_rows.append([
        types.InlineKeyboardButton(
            text=get_text("menu.back_to_menu", lang),
            callback_data="back_to_menu",
        )
    ])

    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data in ("consultant_switch_male", "consultant_switch_female"))
async def on_consultant_switch(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    new_gender = "male" if callback.data == "consultant_switch_male" else "female"
    await update_user_profile(callback.from_user.id, consultant_gender=new_gender)
    await callback.answer(get_text("settings.consultant_switched", lang))
    # Refresh the settings screen
    await on_settings(callback)


@router.callback_query(lambda c: c.data == "redo_onboarding")
async def on_redo_onboarding(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await update_user_profile(callback.from_user.id, onboarding_completed=False)
    await callback.answer()
    client = OpenRouterClient()
    try:
        female_name, male_name = get_consultant_names(None, lang)
        agent = OnboardingAgent(client, model=settings.default_model)
        greeting = await agent.start_message(lang, female_name, male_name, "female")
        set_onboarding_step(callback.from_user.id, 1)
        await callback.message.edit_text(greeting)
    except Exception:
        logger.exception("on_redo_onboarding failed")
        await callback.message.edit_text(
            get_text("start.thanks", lang),
            reply_markup=main_menu_keyboard(lang),
        )
    finally:
        await client.close()


@router.callback_query(lambda c: c.data == "delete_my_data")
async def on_delete_my_data(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    await callback.message.edit_text(
        get_text("privacy.delete_confirm", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("settings.confirm_delete", lang),
                        callback_data="delete_confirmed",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back", lang),
                        callback_data="back_to_menu",
                    )
                ],
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
        clear_onboarding_step(callback.from_user.id)
        text = get_text("privacy.deleted", lang)

    await callback.message.edit_text(text, reply_markup=_back_to_menu_keyboard(lang))
    await callback.answer()
