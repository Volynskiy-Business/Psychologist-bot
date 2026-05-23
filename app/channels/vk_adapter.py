"""VK Community Bot adapter — incoming event mapping and outbound message send."""
from __future__ import annotations

import json
import logging
import secrets
from typing import Any

import httpx

from app.channels.models import Channel, ChannelButton, ChannelMessage, ChannelResponse, ChannelUser

logger = logging.getLogger(__name__)

VK_API_BASE = "https://api.vk.com/method"


def map_message_new(payload: dict[str, Any]) -> ChannelMessage:
    """Map a VK message_new Callback API event to a normalized ChannelMessage."""
    obj = payload["object"]
    message = obj["message"]
    client_info = obj.get("client_info", {})
    return ChannelMessage(
        channel=Channel.VK,
        external_message_id=str(message["id"]),
        external_chat_id=str(message["peer_id"]),
        user=ChannelUser(
            channel=Channel.VK,
            external_user_id=str(message["from_id"]),
            locale="ru",
        ),
        text=message.get("text", ""),
        raw_event_type="message_new",
        raw_payload=payload,
        client_capabilities=client_info,
    )


def _keyboard_supported(client_info: dict[str, Any]) -> bool:
    return bool(client_info.get("keyboard", False))


def _build_vk_keyboard(buttons: list[ChannelButton]) -> str:
    kb = {
        "one_time": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": btn.text[:40],  # VK label limit
                        "payload": btn.payload,
                    },
                    "color": "primary",
                }
            ]
            for btn in buttons
        ],
    }
    return json.dumps(kb, ensure_ascii=False)


def _append_plain_text_options(response: ChannelResponse) -> str:
    if not response.buttons:
        return response.text
    opts = "\n".join(f"{i + 1}. {btn.text}" for i, btn in enumerate(response.buttons))
    return f"{response.text}\n\n{opts}"


async def send_vk_message(
    *,
    response: ChannelResponse,
    peer_id: int,
    client_capabilities: dict[str, Any],
    access_token: str,
    api_version: str,
) -> None:
    """Send a reply via VK messages.send API."""
    keyboard_ok = _keyboard_supported(client_capabilities)

    params: dict[str, Any] = {
        "peer_id": peer_id,
        "random_id": secrets.randbelow(2**31),
        "access_token": access_token,
        "v": api_version,
    }

    if response.buttons and keyboard_ok:
        params["message"] = response.text
        params["keyboard"] = _build_vk_keyboard(response.buttons)
    elif response.buttons:
        params["message"] = _append_plain_text_options(response)
    else:
        params["message"] = response.text

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(f"{VK_API_BASE}/messages.send", data=params)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logger.error(
                    "stage=vk_send status=failed error_code=%s",
                    data["error"].get("error_code", "unknown"),
                )
            else:
                logger.info("stage=vk_send status=success")
        except httpx.HTTPStatusError as exc:
            logger.error(
                "stage=vk_send status=failed error_type=http_error status_code=%d",
                exc.response.status_code,
            )
        except Exception:
            logger.exception("stage=vk_send status=failed error_type=unexpected")
