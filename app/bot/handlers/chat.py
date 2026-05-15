"""Main chat handler with safety checks."""

import logging

import httpx
from aiogram import Router, types
from aiogram.filters import Command

from app.ai.openrouter_client import OpenRouterClient
from app.ai.output_validation import validate_support_response
from app.ai.prompts.system_prompt import SYSTEM_PROMPT
from app.bot.handlers.i18n import get_text, get_user_language
from app.bot.handlers.mood import consume_note_waiter, is_awaiting_note
from app.config import settings
from app.services.user_service import has_consent, record_safety_event, save_mood_note
from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check
from app.safety.safety_classifier import SafetyClassifier
from app.safety.safety_protocols import get_crisis_response

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("chat"))
async def cmd_chat(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    await message.answer(get_text("chat.prompt", lang))


@router.message()
async def handle_message(message: types.Message) -> None:
    if not message.text:
        return

    lang = get_user_language(message.from_user)
    user_text = message.text.strip()

    # Step 1: Deterministic crisis check (runs before consent — no external calls)
    risk_level, pattern = deterministic_crisis_check(user_text)

    if risk_level >= RiskLevel.POSSIBLE_CRISIS:
        try:
            await record_safety_event(
                telegram_user_id=message.from_user.id,
                risk_level=risk_level,
                matched_pattern=pattern,
            )
        except Exception:
            logger.exception("stage=crisis_record Failed to record safety event")
        await message.answer(get_crisis_response(risk_level, lang))
        return

    # Step 1b: Consent gate — block LLM/classifier until user accepts terms
    if not await has_consent(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text=get_text("start.buttons.continue", lang),
                    callback_data="consent_agree",
                )
            ]]
        )
        await message.answer(get_text("chat.consent_required", lang), reply_markup=keyboard)
        return

    # Step 1c: Mood note interception — save free text as a note, skip LLM
    if is_awaiting_note(message.from_user.id):
        consume_note_waiter(message.from_user.id)
        try:
            await save_mood_note(message.from_user.id, user_text)
        except Exception:
            logger.exception("stage=mood_note Failed to save note")
        await message.answer(
            get_text("mood.note_saved", lang),
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]]
            ),
        )
        return

    # Step 2: LLM safety classification (for non-obvious cases)
    client = OpenRouterClient()
    classifier_model = settings.classifier_model or None
    classifier = SafetyClassifier(client, model=classifier_model)

    try:
        classification = await classifier.classify(user_text)
        if classification.risk_level >= RiskLevel.POSSIBLE_CRISIS:
            await message.answer(get_crisis_response(classification.risk_level, lang))
            await client.close()
            return
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("stage=classifier status=429 rate_limited; failing closed")
        else:
            logger.exception("stage=classifier status=%d failing closed", exc.response.status_code)
        await message.answer(get_text("chat.classifier_unavailable", lang))
        await client.close()
        return
    except Exception:
        logger.exception("stage=classifier exception; failing closed")
        await message.answer(get_text("chat.classifier_unavailable", lang))
        await client.close()
        return

    # Step 3: Normal support flow
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        is_safe, block_reason = validate_support_response(response.content)
        if not is_safe:
            logger.warning("stage=output_validation blocked reason=%s", block_reason)
            await message.answer(get_text("chat.output_blocked", lang))
        else:
            await message.answer(response.content)
    except Exception:
        await message.answer(get_text("chat.error", lang))
    finally:
        await client.close()
