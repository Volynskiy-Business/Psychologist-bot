"""Normalized channel models shared across all platform adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Channel(StrEnum):
    TELEGRAM = "telegram"
    VK = "vk"


@dataclass(frozen=True)
class ChannelUser:
    channel: Channel
    external_user_id: str
    locale: str | None = None


@dataclass(frozen=True)
class ChannelMessage:
    channel: Channel
    external_message_id: str
    external_chat_id: str
    user: ChannelUser
    text: str
    raw_event_type: str
    raw_payload: dict[str, Any] = field(default_factory=dict)
    client_capabilities: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChannelButton:
    text: str
    payload: str


@dataclass(frozen=True)
class ChannelResponse:
    text: str
    buttons: list[ChannelButton] | None = None
    disable_rich_ui: bool = False
    crisis_locked: bool = False
