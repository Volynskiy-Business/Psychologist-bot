"""Main chat handler with safety checks."""

import asyncio
import hashlib
import hmac
import logging
from typing import Union

import httpx
from aiogram import Router, types
from aiogram.filters import Command

from app.ai import tracing
from app.ai.agents.anxiety_support import AnxietySupportAgent
from app.ai.agents.friendly_conversation import FriendlyConversationAgent
from app.ai.agents.onboarding_agent import OnboardingAgent, get_consultant_names
from app.ai.agents.sadness_support import SadnessSupportAgent
from app.ai.openrouter_client import OpenRouterClient
from app.ai.orchestration.pipeline import SupportPipeline
from app.ai.routing.intake import classify_intake, detect_language
from app.bot.handlers.i18n import get_text, get_user_language
from app.bot.user_state import (
    MODE_ANXIETY_SUPPORT,
    MODE_FRIENDLY_CHAT,
    MODE_SADNESS_SUPPORT,
    clear_onboarding_step,
    clear_safety_section,
    get_mode,
    get_onboarding_step,
    get_safety_section,
    set_onboarding_step,
)
from app.bot.handlers.feedback import feedback_keyboard
from app.bot.handlers.mood import consume_note_waiter, is_awaiting_note, send_mood_summary
from app.bot.handlers.safety_plan import send_section_view
from app.config import settings
from app.services.safety_plan_service import add_item as add_safety_plan_item
from app.services.user_service import get_user_by_telegram_id, has_consent, record_safety_event, save_mood_note, update_user_profile
from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check
from app.safety.safety_classifier import SafetyClassifier
from app.safety.safety_protocols import get_crisis_response

logger = logging.getLogger(__name__)
router = Router()

# In-memory conversation history keyed by telegram user_id.
# Stores alternating user/assistant dicts; capped at _MAX_HISTORY messages total.
_history: dict[int, list[dict[str, str]]] = {}
_MAX_HISTORY = 20  # 10 exchanges

# Exchange counter for friendly-chat feedback throttling.
# Feedback buttons break conversational flow when shown every turn —
# so in friendly mode we show them only every _FEEDBACK_EVERY_N exchanges.
_friendly_exchange_count: dict[int, int] = {}
_FEEDBACK_EVERY_N = 5


def _get_history(user_id: int) -> list[dict[str, str]]:
    return _history.get(user_id, [])


def _record_exchange(user_id: int, user_text: str, bot_reply: str) -> None:
    h = _history.setdefault(user_id, [])
    h.append({"role": "user", "content": user_text})
    h.append({"role": "assistant", "content": bot_reply})
    if len(h) > _MAX_HISTORY:
        _history[user_id] = h[-_MAX_HISTORY:]


def _friendly_reply_keyboard(user_id: int, lang: str) -> types.InlineKeyboardMarkup | None:
    """No inline keyboard most turns — chat looks like a real conversation.

    Full feedback keyboard surfaces every N-th turn so we still collect ratings
    without interrupting the flow on every message.
    """
    count = _friendly_exchange_count.get(user_id, 0) + 1
    _friendly_exchange_count[user_id] = count
    feedback_due = count > 0 and count % _FEEDBACK_EVERY_N == 0
    logger.info(
        "stage=friendly_keyboard_policy turn_count=%d inline_markup=%s feedback_due=%s",
        count,
        feedback_due,
        feedback_due,
    )
    if feedback_due:
        return feedback_keyboard(lang)
    return None


def _build_context_str(user_id: int) -> str:
    """Return recent conversation as a plain string for the classifier's context field."""
    recent = _get_history(user_id)[-4:]  # last 2 exchanges
    if not recent:
        return ""
    parts = []
    for msg in recent:
        prefix = "Пользователь" if msg["role"] == "user" else "Бот"
        parts.append(f"{prefix}: {msg['content'][:200]}")
    return "\n".join(parts)


def _anon_stable_id(value: int | str, namespace: str) -> str:
    """HMAC-SHA256 stable anonymous ID scoped by namespace.

    Uses TRACING_SALT so raw Telegram IDs cannot be enumerated even if an attacker
    knows the algorithm.  Different namespaces produce different IDs for the same value.

    Imports app.config.settings directly (not the module-level name) so test patches
    of app.bot.handlers.chat.settings do not interfere with the real salt.
    """
    from app.config import settings as _cfg  # bypass module-level mock in tests
    secret = _cfg.tracing_salt.get_secret_value()
    digest = hmac.new(
        key=secret.encode(),
        msg=f"{namespace}:{value}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"{namespace}_{digest[:16]}"


def _back_to_menu_kb(lang: str) -> types.InlineKeyboardMarkup:
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


async def _keep_typing(message: types.Message) -> None:
    """Send typing action every 4 s so the indicator stays alive during slow LLM calls."""
    while True:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        await asyncio.sleep(4)



async def _transcribe_voice_for_chat(message: types.Message) -> str | None:
    """Transcribe Telegram voice using the existing voice_transcription module."""
    from app.ai.voice_transcription import transcribe_voice

    result = await transcribe_voice(message.voice, message.bot)
    if result:
        return str(result).strip()
    return None


@router.message(Command("chat"))
async def cmd_chat(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    await message.answer(get_text("chat.prompt", lang))


@router.message()
async def handle_message(message: types.Message) -> None:
    lang = get_user_language(message.from_user)

    if message.text:
        user_text = message.text.strip()
    elif message.voice:
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            user_text = await _transcribe_voice_for_chat(message)
            logger.info("stage=voice_handler transcript_chars=%d", len(user_text or ""))
        except Exception:
            logger.exception("stage=voice_handler status=failed")
            await message.answer(get_text("chat.error", lang))
            return
        if not user_text:
            logger.warning("stage=voice_handler status=empty_transcript")
            await message.answer(get_text("chat.error", lang))
            return
    else:
        return
    msg_lang = detect_language(user_text)

    # Step 1: Deterministic crisis check (runs before consent — no external calls)
    risk_level, pattern = deterministic_crisis_check(user_text)

    if risk_level >= RiskLevel.POSSIBLE_CRISIS:
        # Clear any pending tool states so the crisis phrase is not later saved as
        # a mood note or safety plan item.
        consume_note_waiter(message.from_user.id)
        clear_safety_section(message.from_user.id)
        try:
            await record_safety_event(
                telegram_user_id=message.from_user.id,
                risk_level=risk_level,
                matched_pattern=pattern,
            )
        except Exception:
            logger.exception("stage=crisis_record Failed to record safety event")
        await message.answer(get_crisis_response(risk_level, msg_lang))
        return

    # Step 1a: Passive-risk phrases — deterministic Tier 2 response, no LLM required
    if risk_level == RiskLevel.ELEVATED_DISTRESS:
        consume_note_waiter(message.from_user.id)
        clear_safety_section(message.from_user.id)
        try:
            await record_safety_event(
                telegram_user_id=message.from_user.id,
                risk_level=risk_level,
                matched_pattern=pattern,
            )
        except Exception:
            logger.exception("stage=crisis_record Failed to record passive-risk event")
        await message.answer(get_crisis_response(RiskLevel.ELEVATED_DISTRESS, msg_lang))
        return

    # Step 1b: Consent gate — block LLM/classifier until user accepts terms
    if not await has_consent(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("start.buttons.continue", lang),
                        callback_data="consent_agree",
                    )
                ]
            ]
        )
        await message.answer(
            get_text("chat.consent_required", lang), reply_markup=keyboard
        )
        return

    # Step 1c: Onboarding interception — handle free-text answers for onboarding steps
    onboarding_step = get_onboarding_step(message.from_user.id)
    if onboarding_step == 0:
        # In-memory step may be lost after bot restart — check DB
        _ob_user = await get_user_by_telegram_id(message.from_user.id)
        if _ob_user is not None and not _ob_user.onboarding_completed:
            from app.bot.handlers.start import _launch_onboarding
            await _launch_onboarding(message.from_user.id, lang, message)
            return
    if onboarding_step > 0:
        client = OpenRouterClient()
        try:
            db_user = await get_user_by_telegram_id(message.from_user.id)
            c_gender = getattr(db_user, "consultant_gender", "female") if db_user else "female"
            country_hint = getattr(db_user, "region", None) if db_user else None
            female_name, male_name = get_consultant_names(country_hint, lang)
            agent = OnboardingAgent(client, model=settings.default_model)

            if onboarding_step == 1:
                # Extract name, gender, country from user's first answer
                extracted = await agent.extract_profile(user_text, female_name, male_name)
                updates: dict = {}
                if extracted.get("name"):
                    updates["display_name"] = extracted["name"]
                if extracted.get("gender") not in (None, "unknown"):
                    updates["gender"] = extracted["gender"]
                if extracted.get("country"):
                    updates["region"] = extracted["country"]
                    # Refresh names based on detected country
                    female_name, male_name = get_consultant_names(extracted["country"], lang)
                if updates:
                    await update_user_profile(message.from_user.id, **updates)
                # Also check if consultant_gender slipped in (unlikely but possible)
                if extracted.get("consultant_gender") not in (None, "unknown"):
                    await update_user_profile(
                        message.from_user.id,
                        consultant_gender=extracted["consultant_gender"],
                    )
                    c_gender = extracted["consultant_gender"]
                # Move to step 2
                set_onboarding_step(message.from_user.id, 2)
                step2_msg = await agent.step2_message(
                    lang, female_name, male_name, c_gender,
                    user_name=extracted.get("name"),
                )
                await message.answer(step2_msg)

            elif onboarding_step == 2:
                # Extract consultant gender preference
                extracted = await agent.extract_profile(user_text, female_name, male_name)
                c_pref = extracted.get("consultant_gender")
                if c_pref and c_pref not in ("unknown",):
                    await update_user_profile(
                        message.from_user.id, consultant_gender=c_pref
                    )
                    c_gender = c_pref
                # Re-load display_name for closing message
                db_user2 = await get_user_by_telegram_id(message.from_user.id)
                consultant_name = (
                    male_name if c_gender == "male" else female_name
                )
                user_name = getattr(db_user2, "display_name", None) if db_user2 else None
                # Mark onboarding complete
                await update_user_profile(
                    message.from_user.id, onboarding_completed=True
                )
                clear_onboarding_step(message.from_user.id)
                done_msg = await agent.done_message(lang, consultant_name, c_gender, user_name)
                from app.bot.handlers.start import main_menu_keyboard
                await message.answer(done_msg)
                await message.answer(
                    get_text("start.thanks", lang),
                    reply_markup=main_menu_keyboard(lang),
                )
        except Exception:
            logger.exception("Onboarding step %d failed", onboarding_step)
            clear_onboarding_step(message.from_user.id)
            # Do NOT mark onboarding_completed=True here — let the user retry via /start
            from app.bot.handlers.start import main_menu_keyboard
            await message.answer(
                get_text("chat.error", lang),
                reply_markup=main_menu_keyboard(lang),
            )
        finally:
            await client.close()
        return

    # Step 1c: Mood note interception — save free text as a note, skip LLM
    if is_awaiting_note(message.from_user.id):
        consume_note_waiter(message.from_user.id)
        try:
            await save_mood_note(message.from_user.id, user_text)
        except Exception:
            logger.exception("stage=mood_note Failed to save note")
        await message.answer(get_text("mood.note_saved", lang))
        await send_mood_summary(message, message.from_user.id, lang)
        return

    # Step 1d: Safety plan item interception — save text to active section, skip LLM
    section = get_safety_section(message.from_user.id)
    if section:
        clear_safety_section(message.from_user.id)
        try:
            await add_safety_plan_item(message.from_user.id, section, user_text)
        except Exception:
            logger.exception("stage=safety_plan Failed to save item section=%s", section)
        await send_section_view(message, message.from_user.id, section, lang)
        return

    # Step 2: LLM safety classification — only when CLASSIFIER_MODEL is explicitly configured
    client = OpenRouterClient()
    if settings.classifier_model:
        classifier = SafetyClassifier(
            client,
            model=settings.classifier_model,
            fallback_models=settings.fallback_models,
        )
        context_str = _build_context_str(message.from_user.id)
        try:
            classification = await classifier.classify(user_text, context=context_str)
            if classification.risk_level >= RiskLevel.POSSIBLE_CRISIS:
                await message.answer(
                    get_crisis_response(classification.risk_level, msg_lang)
                )
                await client.close()
                return
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning(
                    "stage=classifier status=429 rate_limited; failing closed"
                )
            else:
                logger.exception(
                    "stage=classifier status=%d failing closed",
                    exc.response.status_code,
                )
            await message.answer(
                get_text("chat.classifier_unavailable", lang),
                reply_markup=_back_to_menu_kb(lang),
            )
            await client.close()
            return
        except Exception:
            logger.exception("stage=classifier exception; failing closed")
            await message.answer(
                get_text("chat.classifier_unavailable", lang),
                reply_markup=_back_to_menu_kb(lang),
            )
            await client.close()
            return

    # Step 3: Route to the appropriate agent based on user mode.
    # If no explicit mode is set, auto-detect sadness signals (deterministic, no LLM).
    user_mode = get_mode(message.from_user.id)
    if not user_mode:
        quick = classify_intake(user_text, msg_lang)
        if quick.detected_emotion in ("sadness", "grief"):
            user_mode = MODE_SADNESS_SUPPORT

    # Load user profile for personalization
    db_user = await get_user_by_telegram_id(message.from_user.id)
    user_profile: dict | None = None
    if db_user:
        country = getattr(db_user, "region", None)
        c_gender = getattr(db_user, "consultant_gender", "female")
        female_name, male_name = get_consultant_names(country, lang)
        consultant_name = male_name if c_gender == "male" else female_name
        user_profile = {
            "consultant_gender": c_gender,
            "consultant_name": consultant_name,
            "display_name": getattr(db_user, "display_name", None),
            "gender": getattr(db_user, "gender", None),
            "region": country,
        }
    logger.info(
        "stage=friendly_mode_detected value=%s effective_mode=%s",
        user_mode == MODE_FRIENDLY_CHAT,
        user_mode or "pipeline",
    )

    history = _get_history(message.from_user.id)
    # Only compute HMAC IDs when Langfuse is active; avoids work and salt access otherwise.
    _enabled = tracing.is_enabled()
    with tracing.tracing_context(
        session_id=_anon_stable_id(message.chat.id, "tg_chat") if _enabled else None,
        user_id=_anon_stable_id(message.from_user.id, "tg_user") if _enabled else None,
    ):
        typing_task = asyncio.create_task(_keep_typing(message))
        try:
            result = None
            for model in [settings.default_model] + settings.fallback_models:
                agent: Union[
                    FriendlyConversationAgent, AnxietySupportAgent,
                    SadnessSupportAgent, SupportPipeline
                ]
                if user_mode == MODE_FRIENDLY_CHAT:
                    agent = FriendlyConversationAgent(client, model=model)
                elif user_mode == MODE_ANXIETY_SUPPORT:
                    agent = AnxietySupportAgent(client, model=model)
                elif user_mode == MODE_SADNESS_SUPPORT:
                    agent = SadnessSupportAgent(client, model=model)
                else:
                    agent = SupportPipeline(client, model=model)
                try:
                    result = await agent.run(user_text, msg_lang, history, user_profile)
                    logger.debug("stage=support_generation model=%s status=success", model)
                    break
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "stage=support_generation model=%s status=%d; trying next",
                        model,
                        exc.response.status_code,
                    )
                except Exception:
                    logger.exception(
                        "stage=support_generation model=%s status=exception", model
                    )
                    break
            if result is None:
                await message.answer(
                    get_text("chat.error", lang), reply_markup=_back_to_menu_kb(lang)
                )
            elif not result.is_safe:
                logger.warning(
                    "stage=output_validation blocked reason=%s", result.block_reason
                )
                await message.answer(
                    get_text("chat.output_blocked", lang),
                    reply_markup=_back_to_menu_kb(lang),
                )
            else:
                _record_exchange(message.from_user.id, user_text, result.content)
                if get_mode(message.from_user.id) == MODE_FRIENDLY_CHAT:
                    kb = _friendly_reply_keyboard(message.from_user.id, lang)
                else:
                    kb = feedback_keyboard(lang)
                await message.answer(result.content, reply_markup=kb)
        except Exception:
            await message.answer(
                get_text("chat.error", lang), reply_markup=_back_to_menu_kb(lang)
            )
        finally:
            typing_task.cancel()
            await client.close()
