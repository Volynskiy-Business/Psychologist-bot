"""Main chat handler with safety checks."""

import logging

from aiogram import Router, types
from aiogram.filters import Command

from app.ai.openrouter_client import OpenRouterClient
from app.ai.prompts.system_prompt import SYSTEM_PROMPT
from app.bot.handlers.i18n import get_text, get_user_language
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

    # Step 1: Deterministic crisis check
    risk_level, pattern = deterministic_crisis_check(user_text)

    if risk_level >= RiskLevel.POSSIBLE_CRISIS:
        await message.answer(get_crisis_response(risk_level, lang))
        return

    # Step 2: LLM safety classification (for non-obvious cases)
    client = OpenRouterClient()
    classifier = SafetyClassifier(client)

    try:
        classification = await classifier.classify(user_text)
        if classification.risk_level >= RiskLevel.POSSIBLE_CRISIS:
            await message.answer(get_crisis_response(classification.risk_level, lang))
            await client.close()
            return
    except Exception:
        logger.exception("Safety classifier failed; failing closed")
        await message.answer(get_text("chat.error", lang))
        await client.close()
        return

    # Step 3: Normal support flow
    await message.chat.do_action("typing")

    try:
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        await message.answer(response.content)
    except Exception as e:
        await message.answer(get_text("chat.error", lang))
    finally:
        await client.close()
