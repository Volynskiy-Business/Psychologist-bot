"""Tests for VK Callback API webhook endpoint.

Covers: confirmation, group_id validation, secret validation, message_new routing,
unsupported events, and duplicate handling.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.channels.models import ChannelResponse


def _make_client(
    *,
    group_id: int = 12345,
    callback_secret: str = "",
    confirmation_token: str = "confirm-abc",
    access_token: str | None = None,
    api_version: str = "5.199",
    vk_webhook_port: int = 8080,
) -> TestClient:
    from app.integrations.web_app import create_web_app

    app = create_web_app()
    client = TestClient(app, raise_server_exceptions=True)
    # Patch settings on the vk module directly (imported at module level)
    mock_cfg = MagicMock()
    mock_cfg.vk_group_id = group_id
    mock_cfg.vk_callback_secret = callback_secret
    mock_cfg.vk_confirmation_token = confirmation_token
    mock_cfg.vk_access_token = access_token
    mock_cfg.vk_api_version = api_version
    mock_cfg.vk_webhook_port = vk_webhook_port
    client._mock_cfg = mock_cfg
    return client


_CONFIRMATION_PAYLOAD = {"type": "confirmation", "group_id": 12345}

_MESSAGE_PAYLOAD = {
    "type": "message_new",
    "group_id": 12345,
    "secret": "",
    "object": {
        "message": {
            "id": 1001,
            "from_id": 456789,
            "peer_id": 456789,
            "text": "Привет",
        },
        "client_info": {"keyboard": False, "inline_keyboard": False},
    },
}


# ---------------------------------------------------------------------------
# Test 1: confirmation returns exact token as plain text
# ---------------------------------------------------------------------------

def test_confirmation_returns_token() -> None:
    with patch("app.integrations.webhooks.vk.settings") as mock_cfg:
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "confirm-abc"
        mock_cfg.vk_access_token = None

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        resp = client.post("/integrations/vk/webhook", json=_CONFIRMATION_PAYLOAD)

    assert resp.status_code == 200
    assert resp.text == "confirm-abc"
    assert resp.headers["content-type"].startswith("text/plain")


# ---------------------------------------------------------------------------
# Test 2: wrong group_id is rejected with 403
# ---------------------------------------------------------------------------

def test_wrong_group_id_rejected() -> None:
    with patch("app.integrations.webhooks.vk.settings") as mock_cfg:
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "tok"

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        resp = client.post(
            "/integrations/vk/webhook",
            json={"type": "confirmation", "group_id": 99999},
        )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 3: invalid callback secret is rejected with 403
# ---------------------------------------------------------------------------

def test_invalid_secret_rejected() -> None:
    with patch("app.integrations.webhooks.vk.settings") as mock_cfg:
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = "correct-secret"
        mock_cfg.vk_confirmation_token = "tok"
        mock_cfg.vk_access_token = None

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        payload = dict(_CONFIRMATION_PAYLOAD)
        payload["secret"] = "wrong-secret"
        resp = client.post("/integrations/vk/webhook", json=payload)

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 4: message_new returns plain text "ok"
# ---------------------------------------------------------------------------

async def test_message_new_returns_ok() -> None:
    fake_response = ChannelResponse(text="Привет! Как ты?")

    with (
        patch("app.integrations.webhooks.vk.settings") as mock_cfg,
        patch(
            "app.integrations.webhooks.vk.process_channel_message",
            new=AsyncMock(return_value=fake_response),
        ),
    ):
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "tok"
        mock_cfg.vk_access_token = None
        mock_cfg.vk_api_version = "5.199"

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        resp = client.post("/integrations/vk/webhook", json=_MESSAGE_PAYLOAD)

    assert resp.status_code == 200
    assert resp.text == "ok"


# ---------------------------------------------------------------------------
# Test 5: unsupported event type returns "ok" (not an error)
# ---------------------------------------------------------------------------

def test_unsupported_event_returns_ok() -> None:
    with patch("app.integrations.webhooks.vk.settings") as mock_cfg:
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "tok"
        mock_cfg.vk_access_token = None

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        resp = client.post(
            "/integrations/vk/webhook",
            json={"type": "group_join", "group_id": 12345},
        )

    assert resp.status_code == 200
    assert resp.text == "ok"


# ---------------------------------------------------------------------------
# Test 6: duplicate message_new is ignored (returns "ok", pipeline not called)
# ---------------------------------------------------------------------------

async def test_duplicate_event_not_processed_twice() -> None:
    fake_response = ChannelResponse(text="response")
    pipeline_mock = AsyncMock(return_value=fake_response)

    # Clear deduplication state before test
    import app.integrations.webhooks.vk as vk_mod
    vk_mod._seen_events.clear()

    with (
        patch("app.integrations.webhooks.vk.settings") as mock_cfg,
        patch("app.integrations.webhooks.vk.process_channel_message", new=pipeline_mock),
    ):
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "tok"
        mock_cfg.vk_access_token = None
        mock_cfg.vk_api_version = "5.199"

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        client.post("/integrations/vk/webhook", json=_MESSAGE_PAYLOAD)
        client.post("/integrations/vk/webhook", json=_MESSAGE_PAYLOAD)

    assert pipeline_mock.call_count == 1


# ---------------------------------------------------------------------------
# Test 7: message from community itself (negative from_id) is ignored
# ---------------------------------------------------------------------------

async def test_community_self_message_ignored() -> None:
    pipeline_mock = AsyncMock(return_value=ChannelResponse(text="x"))

    self_msg_payload = {
        "type": "message_new",
        "group_id": 12345,
        "secret": "",
        "object": {
            "message": {
                "id": 2002,
                "from_id": -12345,  # negative = community/bot
                "peer_id": 456789,
                "text": "Automated message",
            },
            "client_info": {},
        },
    }

    with (
        patch("app.integrations.webhooks.vk.settings") as mock_cfg,
        patch("app.integrations.webhooks.vk.process_channel_message", new=pipeline_mock),
    ):
        mock_cfg.vk_group_id = 12345
        mock_cfg.vk_callback_secret = ""
        mock_cfg.vk_confirmation_token = "tok"
        mock_cfg.vk_access_token = None

        from app.integrations.web_app import create_web_app
        client = TestClient(create_web_app())
        resp = client.post("/integrations/vk/webhook", json=self_msg_payload)

    assert resp.status_code == 200
    pipeline_mock.assert_not_called()
