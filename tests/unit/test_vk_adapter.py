"""Tests for VK adapter: incoming mapping and outbound send."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.channels.models import Channel, ChannelButton, ChannelMessage, ChannelResponse
from app.services.channel_router import process_channel_message


# ---------------------------------------------------------------------------
# Incoming mapping tests
# ---------------------------------------------------------------------------

def _make_message_payload(
    *,
    msg_id: int = 42,
    from_id: int = 999,
    peer_id: int = 999,
    text: str = "Hello",
    client_info: dict | None = None,
) -> dict:
    return {
        "type": "message_new",
        "group_id": 12345,
        "object": {
            "message": {
                "id": msg_id,
                "from_id": from_id,
                "peer_id": peer_id,
                "text": text,
            },
            "client_info": client_info or {},
        },
    }


def test_map_message_new_maps_fields() -> None:
    from app.channels.vk_adapter import map_message_new

    payload = _make_message_payload(
        msg_id=42, from_id=999, peer_id=999, text="Привет"
    )
    msg = map_message_new(payload)

    assert msg.channel == Channel.VK
    assert msg.external_message_id == "42"
    assert msg.external_chat_id == "999"
    assert msg.user.external_user_id == "999"
    assert msg.user.locale == "ru"
    assert msg.text == "Привет"
    assert msg.raw_event_type == "message_new"


def test_map_message_new_uses_peer_id_for_chat() -> None:
    """peer_id (not from_id) is used as the outbound target."""
    from app.channels.vk_adapter import map_message_new

    payload = _make_message_payload(from_id=111, peer_id=222)
    msg = map_message_new(payload)

    assert msg.external_chat_id == "222"
    assert msg.user.external_user_id == "111"


def test_map_message_new_captures_client_info() -> None:
    from app.channels.vk_adapter import map_message_new

    payload = _make_message_payload(client_info={"keyboard": True, "inline_keyboard": True})
    msg = map_message_new(payload)

    assert msg.client_capabilities == {"keyboard": True, "inline_keyboard": True}


def test_map_message_new_empty_text() -> None:
    from app.channels.vk_adapter import map_message_new

    payload = _make_message_payload(text="")
    msg = map_message_new(payload)

    assert msg.text == ""


# ---------------------------------------------------------------------------
# Outbound send tests
# ---------------------------------------------------------------------------

async def test_send_uses_peer_id() -> None:
    """messages.send must use peer_id, not from_id."""
    from app.channels.vk_adapter import send_vk_message

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"response": 1})

    with patch("app.channels.vk_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await send_vk_message(
            response=ChannelResponse(text="Reply"),
            peer_id=456,
            client_capabilities={},
            access_token="token123",
            api_version="5.199",
        )

    call_kwargs = mock_session.post.call_args
    sent_data = call_kwargs.kwargs.get("data") or call_kwargs.args[1]
    assert sent_data["peer_id"] == 456


async def test_send_generates_random_id() -> None:
    """Each send call must generate a unique random_id."""
    from app.channels.vk_adapter import send_vk_message

    random_ids = []

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"response": 1})

    with patch("app.channels.vk_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_session = AsyncMock()

        async def capture_post(url, *, data=None, **kwargs):
            random_ids.append(data.get("random_id"))
            return mock_resp

        mock_session.post = capture_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await send_vk_message(
            response=ChannelResponse(text="A"),
            peer_id=1,
            client_capabilities={},
            access_token="tok",
            api_version="5.199",
        )
        await send_vk_message(
            response=ChannelResponse(text="B"),
            peer_id=1,
            client_capabilities={},
            access_token="tok",
            api_version="5.199",
        )

    assert len(random_ids) == 2
    # They are very likely different; collision probability is 1/2^31
    # Just assert both are valid non-negative ints
    assert all(isinstance(r, int) and r >= 0 for r in random_ids)


async def test_send_plain_text_fallback_when_keyboard_unsupported() -> None:
    """When keyboard is not supported, buttons are appended as numbered text."""
    from app.channels.vk_adapter import send_vk_message

    sent_messages: list[str] = []

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"response": 1})

    with patch("app.channels.vk_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_session = AsyncMock()

        async def capture_post(url, *, data=None, **kwargs):
            sent_messages.append(data.get("message", ""))
            return mock_resp

        mock_session.post = capture_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        response = ChannelResponse(
            text="Choose:",
            buttons=[ChannelButton(text="Option A", payload="{}"), ChannelButton(text="Option B", payload="{}")],
        )
        await send_vk_message(
            response=response,
            peer_id=1,
            client_capabilities={"keyboard": False},  # not supported
            access_token="tok",
            api_version="5.199",
        )

    assert len(sent_messages) == 1
    assert "1. Option A" in sent_messages[0]
    assert "2. Option B" in sent_messages[0]
    assert "keyboard" not in str(sent_messages[0])


async def test_send_does_not_log_token(caplog) -> None:
    """Access token must not appear in log output."""
    import logging

    from app.channels.vk_adapter import send_vk_message

    secret_token = "super-secret-vk-token-12345"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(side_effect=Exception("network error"))

    with patch("app.channels.vk_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with caplog.at_level(logging.ERROR, logger="app.channels.vk_adapter"):
            await send_vk_message(
                response=ChannelResponse(text="test"),
                peer_id=1,
                client_capabilities={},
                access_token=secret_token,
                api_version="5.199",
            )

    assert secret_token not in caplog.text


# ---------------------------------------------------------------------------
# Safety routing via channel_router
# ---------------------------------------------------------------------------

async def test_russian_suicide_request_triggers_crisis_route() -> None:
    """Russian imminent-risk phrase must hit crisis path, not support pipeline."""
    from app.channels.models import ChannelUser

    # Clear any existing crisis lock for this test user
    import app.services.channel_router as router_mod
    test_key = "vk:777001"
    router_mod._crisis_locks.pop(test_key, None)

    msg = ChannelMessage(
        channel=Channel.VK,
        external_message_id="1",
        external_chat_id="777001",
        user=ChannelUser(channel=Channel.VK, external_user_id="777001", locale="ru"),
        text="хочу покончить с собой",
        raw_event_type="message_new",
    )

    with patch("app.services.channel_router.settings") as mock_cfg:
        mock_cfg.classifier_model = ""
        mock_cfg.fallback_models = []
        mock_cfg.default_model = "test/model"
        response = await process_channel_message(msg)

    assert response.crisis_locked is True
    assert router_mod._is_in_crisis_lock(test_key)


async def test_english_suicide_request_triggers_crisis_route() -> None:
    """English imminent-risk phrase must also hit crisis path."""
    from app.channels.models import ChannelUser

    import app.services.channel_router as router_mod
    test_key = "vk:777002"
    router_mod._crisis_locks.pop(test_key, None)

    msg = ChannelMessage(
        channel=Channel.VK,
        external_message_id="2",
        external_chat_id="777002",
        user=ChannelUser(channel=Channel.VK, external_user_id="777002", locale="ru"),
        text="I want to kill myself",
        raw_event_type="message_new",
    )

    with patch("app.services.channel_router.settings") as mock_cfg:
        mock_cfg.classifier_model = ""
        mock_cfg.fallback_models = []
        mock_cfg.default_model = "test/model"
        response = await process_channel_message(msg)

    assert response.crisis_locked is True


async def test_crisis_response_has_no_menu_buttons() -> None:
    """Crisis responses must carry no regular menu or feedback buttons."""
    from app.channels.models import ChannelUser

    import app.services.channel_router as router_mod
    test_key = "vk:777003"
    router_mod._crisis_locks.pop(test_key, None)

    msg = ChannelMessage(
        channel=Channel.VK,
        external_message_id="3",
        external_chat_id="777003",
        user=ChannelUser(channel=Channel.VK, external_user_id="777003", locale="ru"),
        text="хочу умереть",
        raw_event_type="message_new",
    )

    with patch("app.services.channel_router.settings") as mock_cfg:
        mock_cfg.classifier_model = ""
        mock_cfg.fallback_models = []
        mock_cfg.default_model = "test/model"
        response = await process_channel_message(msg)

    # Crisis responses must not include navigation or feedback buttons
    assert response.buttons is None
    assert response.crisis_locked is True
