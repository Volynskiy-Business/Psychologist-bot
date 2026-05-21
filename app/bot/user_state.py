"""Per-user transient state — in-memory, not persisted across restarts."""

_mode: dict[int, str] = {}
_safety_section: dict[int, str] = {}  # user_id → section key being edited
_onboarding_step: dict[int, int] = {}  # user_id → 1 (name/country) | 2 (consultant)

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


# ── Onboarding step tracking ───────────────────────────────────────────────────
# 0 = not in onboarding; 1 = awaiting name/country; 2 = awaiting consultant pref

def set_onboarding_step(user_id: int, step: int) -> None:
    if step == 0:
        _onboarding_step.pop(user_id, None)
    else:
        _onboarding_step[user_id] = step


def get_onboarding_step(user_id: int) -> int:
    return _onboarding_step.get(user_id, 0)


def clear_onboarding_step(user_id: int) -> None:
    _onboarding_step.pop(user_id, None)
