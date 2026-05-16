"""Per-user transient state — in-memory, not persisted across restarts."""

_mode: dict[int, str] = {}
_safety_section: dict[int, str] = {}  # user_id → section key being edited

MODE_FRIENDLY_CHAT = "friendly_chat"
MODE_ANXIETY_SUPPORT = "anxiety_support"
MODE_SADNESS_SUPPORT = "sadness_support"


def set_mode(user_id: int, mode: str) -> None:
    _mode[user_id] = mode


def get_mode(user_id: int) -> str:
    return _mode.get(user_id, "")


def clear_mode(user_id: int) -> None:
    _mode.pop(user_id, None)


def set_safety_section(user_id: int, section: str) -> None:
    _safety_section[user_id] = section


def get_safety_section(user_id: int) -> str | None:
    return _safety_section.get(user_id)


def clear_safety_section(user_id: int) -> None:
    _safety_section.pop(user_id, None)
