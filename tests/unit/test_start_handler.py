"""Tests for /start handler — returning user vs new user routing.

ST-1: consented user gets main menu directly (not consent screen)
ST-2: new (unconsented) user gets consent screen
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_message(user_id: int = 99) -> MagicMock:
    from_user = MagicMock()
    from_user.language_code = "en"
    from_user.id = user_id

    msg = MagicMock()
    msg.from_user = from_user
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_cmd_start_consented_user_sees_main_menu() -> None:
    """ST-1: /start for a returning consented user shows the main menu, not consent screen."""
    from app.bot.handlers.start import cmd_start

    msg = _make_message(user_id=42)

    with patch("app.bot.handlers.start.has_consent", new_callable=AsyncMock, return_value=True):
        await cmd_start(msg)

    msg.answer.assert_called_once()
    text_sent = msg.answer.call_args.args[0]
    # Main menu uses start.thanks text; consent screen uses start.greeting
    assert "Thanks for your trust" in text_sent
    assert "I'm PsySupport AI" not in text_sent


@pytest.mark.asyncio
async def test_cmd_start_new_user_sees_consent_screen() -> None:
    """ST-2: /start for a new unconsented user shows the full consent screen."""
    from app.bot.handlers.start import cmd_start

    msg = _make_message(user_id=77)

    with patch("app.bot.handlers.start.has_consent", new_callable=AsyncMock, return_value=False):
        await cmd_start(msg)

    msg.answer.assert_called_once()
    text_sent = msg.answer.call_args.args[0]
    assert "PsySupport AI" in text_sent
