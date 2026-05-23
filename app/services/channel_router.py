"""Core processing pipeline shared across all inbound channels (VK, future channels).

Telegram continues to use app.bot.handlers.chat directly and is NOT routed here.
This module handles VK messages and any future platform adapters.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.ai.openrouter_client import OpenRouterClient
from app.ai.routing.intake import detect_language
from app.bot.handlers.i18n import get_text
from app.channels.models import ChannelMessage, ChannelResponse
from app.config import settings
from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check
from app.safety.safety_classifier import SafetyClassifier
from app.safety.safety_protocols import get_crisis_response

logger = logging.getLogger(__name__)

# Per-channel-user in-memory state — kept separate from Telegram's user_state.py
# to prevent ID namespace collisions between platforms.
_crisis_locks: dict[str, float] = {}   # "{channel}:{user_id}" → expiry timestamp
_conv_history: dict[str, list[dict]] = {}   # "{channel}:{user_id}" → message list
_MAX_HISTORY = 20
_CRISIS_LOCK_TTL = 3600  # 60 minutes


def _user_key(msg: ChannelMessage) -> str:
    return f"{msg.channel}:{msg.user.external_user_id}"


def _is_in_crisis_lock(key: str) -> bool:
    expiry = _crisis_locks.get(key)
    if expiry is None:
        return False
    if time.time() > expiry:
        _crisis_locks.pop(key, None)
        return False
    return True


def _set_crisis_lock(key: str) -> None:
    _crisis_locks[key] = time.time() + _CRISIS_LOCK_TTL


def _get_history(key: str) -> list[dict]:
    return _conv_history.get(key, [])


def _record_history(key: str, user_text: str, bot_reply: str) -> None:
    h = _conv_history.setdefault(key, [])
    h.append({"role": "user", "content": user_text})
    h.append({"role": "assistant", "content": bot_reply})
    if len(h) > _MAX_HISTORY:
        _conv_history[key] = h[-_MAX_HISTORY:]


async def process_channel_message(msg: ChannelMessage) -> ChannelResponse:
    """Shared pipeline: crisis lock → crisis detection → classifier → support agent.

    Phase 1 notes:
    - Consent gate is skipped for VK (all inbound VK DMs are treated as consented).
    - Safety events are logged only; DB persistence is a Phase 2 item.
    - Mode selection (friendly/anxiety/sadness) uses SupportPipeline default.
    """
    key = _user_key(msg)
    locale = msg.user.locale or "ru"
    msg_lang = detect_language(msg.text) or locale

    # Step 0: Crisis lock — re-route active crisis users without pipeline
    if _is_in_crisis_lock(key):
        logger.info("stage=channel_router channel=%s status=crisis_locked", msg.channel)
        return ChannelResponse(
            text=get_text("crisis.tier4_free_text", msg_lang),
            crisis_locked=True,
        )

    # Step 1: Deterministic crisis detection (no external calls)
    risk_level, pattern = deterministic_crisis_check(msg.text)

    if risk_level >= RiskLevel.IMMINENT_RISK:
        _set_crisis_lock(key)
        logger.warning(
            "stage=channel_router channel=%s status=imminent_risk pattern=%s",
            msg.channel,
            bool(pattern),
        )
        return ChannelResponse(
            text=get_text("crisis.tier4_response", msg_lang),
            crisis_locked=True,
        )

    if risk_level == RiskLevel.POSSIBLE_CRISIS:
        logger.warning("stage=channel_router channel=%s status=possible_crisis", msg.channel)
        return ChannelResponse(text=get_crisis_response(risk_level, msg_lang))

    if risk_level == RiskLevel.ELEVATED_DISTRESS:
        logger.warning("stage=channel_router channel=%s status=elevated_distress", msg.channel)
        return ChannelResponse(text=get_crisis_response(RiskLevel.ELEVATED_DISTRESS, msg_lang))

    # Step 2: LLM safety classifier (only when CLASSIFIER_MODEL is configured)
    client = OpenRouterClient()
    if settings.classifier_model:
        classifier = SafetyClassifier(
            client,
            model=settings.classifier_model,
            fallback_models=settings.fallback_models,
        )
        try:
            classification = await classifier.classify(msg.text)
            if classification.risk_level >= RiskLevel.IMMINENT_RISK:
                _set_crisis_lock(key)
                await client.close()
                return ChannelResponse(
                    text=get_text("crisis.tier4_response", msg_lang),
                    crisis_locked=True,
                )
            if classification.risk_level >= RiskLevel.POSSIBLE_CRISIS:
                await client.close()
                return ChannelResponse(text=get_crisis_response(classification.risk_level, msg_lang))
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "stage=channel_router classifier status=%d failing_closed",
                exc.response.status_code,
            )
            await client.close()
            return ChannelResponse(text=get_text("chat.classifier_unavailable", locale))
        except Exception:
            logger.exception("stage=channel_router classifier exception failing_closed")
            await client.close()
            return ChannelResponse(text=get_text("chat.classifier_unavailable", locale))

    # Step 3: Support pipeline
    from app.ai.orchestration.pipeline import SupportPipeline

    history = _get_history(key)
    result = None
    for model in [settings.default_model] + settings.fallback_models:
        agent = SupportPipeline(client, model=model)
        try:
            result = await agent.run(msg.text, msg_lang, history)
            logger.debug(
                "stage=channel_router channel=%s model=%s status=success",
                msg.channel, model,
            )
            break
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "stage=channel_router channel=%s model=%s status=%d trying_next",
                msg.channel, model, exc.response.status_code,
            )
        except Exception:
            logger.exception(
                "stage=channel_router channel=%s model=%s exception",
                msg.channel, model,
            )
            break

    await client.close()

    if result is None:
        return ChannelResponse(text=get_text("chat.error", locale))

    if not result.is_safe:
        logger.warning(
            "stage=channel_router output_blocked reason=%s", result.block_reason
        )
        return ChannelResponse(text=get_text("chat.output_blocked", locale))

    _record_history(key, msg.text, result.content)
    logger.info("stage=channel_router channel=%s status=completed", msg.channel)
    return ChannelResponse(text=result.content)
