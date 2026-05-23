"""VK Callback API webhook endpoint."""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.channels.vk_adapter import map_message_new, send_vk_message
from app.config import settings
from app.services.channel_router import process_channel_message

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory deduplication cache: key → expiry timestamp
_seen_events: dict[str, float] = {}
_IDEMPOTENCY_TTL = 300  # 5 minutes


def _is_duplicate(key: str) -> bool:
    expiry = _seen_events.get(key)
    if expiry is None:
        return False
    if time.time() > expiry:
        _seen_events.pop(key, None)
        return False
    return True


def _mark_seen(key: str) -> None:
    _seen_events[key] = time.time() + _IDEMPOTENCY_TTL


@router.post("/integrations/vk/webhook")
async def vk_webhook(request: Request) -> PlainTextResponse:
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    group_id = payload.get("group_id")
    event_type = payload.get("type")

    logger.info(
        "stage=vk_webhook status=received event=%s group_id=%s",
        event_type,
        group_id,
    )

    # Validate group_id when configured
    if settings.vk_group_id and group_id != settings.vk_group_id:
        logger.warning("stage=vk_webhook status=rejected reason=wrong_group_id")
        raise HTTPException(status_code=403, detail="Wrong group_id")

    # Validate callback secret when configured
    incoming_secret = payload.get("secret", "")
    if settings.vk_callback_secret and incoming_secret != settings.vk_callback_secret:
        logger.warning("stage=vk_webhook status=rejected reason=invalid_secret")
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Confirmation handshake — VK requires exact plain-text response
    if event_type == "confirmation":
        logger.info("stage=vk_webhook status=confirmation")
        return PlainTextResponse(settings.vk_confirmation_token)

    # message_new — normalize and process
    if event_type == "message_new":
        try:
            msg = map_message_new(payload)
        except (KeyError, TypeError):
            logger.warning("stage=vk_webhook status=malformed event=message_new")
            return PlainTextResponse("ok")

        # Ignore empty messages and community/bot self-messages (negative from_id)
        if not msg.text.strip():
            return PlainTextResponse("ok")
        if int(msg.user.external_user_id) < 0:
            return PlainTextResponse("ok")

        # Idempotency — VK may deliver the same event multiple times
        idem_key = f"vk:{group_id}:{msg.external_message_id}"
        if _is_duplicate(idem_key):
            logger.info("stage=vk_webhook status=duplicate key=%s", idem_key)
            return PlainTextResponse("ok")
        _mark_seen(idem_key)

        logger.info("stage=vk_message status=normalized")

        response = await process_channel_message(msg)

        if settings.vk_access_token:
            await send_vk_message(
                response=response,
                peer_id=int(msg.external_chat_id),
                client_capabilities=msg.client_capabilities,
                access_token=settings.vk_access_token.get_secret_value(),
                api_version=settings.vk_api_version,
            )

        return PlainTextResponse("ok")

    # Unknown event type — acknowledge to prevent VK retries
    logger.info("stage=vk_webhook status=ignored event=%s", event_type)
    return PlainTextResponse("ok")
