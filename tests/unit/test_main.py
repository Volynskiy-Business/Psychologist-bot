"""Tests for application startup — command registration (CR-1, CR-2)."""


def test_bot_commands_registered_on_startup() -> None:
    """CR-1: _BOT_COMMANDS contains the expected slash commands."""
    from app.main import _BOT_COMMANDS

    commands = {c.command for c in _BOT_COMMANDS}
    assert "start" in commands
    assert "chat" in commands
    assert "mood" in commands


def test_bot_command_descriptions_contain_no_secrets() -> None:
    """CR-2: Command descriptions must not contain tokens or sensitive substrings."""
    from app.main import _BOT_COMMANDS

    for cmd in _BOT_COMMANDS:
        lower = cmd.description.lower()
        assert "token" not in lower
        assert "secret" not in lower
        assert "key" not in lower
