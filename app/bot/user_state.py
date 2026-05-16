"""Per-user transient state — in-memory, not persisted across restarts."""

_mode: dict[int, str] = {}

MODE_FRIENDLY_CHAT = "friendly_chat"
MODE_ANXIETY_SUPPORT = "anxiety_support"


def set_mode(user_id: int, mode: str) -> None:
    _mode[user_id] = mode


def get_mode(user_id: int) -> str:
    return _mode.get(user_id, "")


def clear_mode(user_id: int) -> None:
    _mode.pop(user_id, None)
