"""Tests for Talk Mode keyboard policy.

Verifies that friendly-chat turns show no inline keyboard most of the time,
and surface feedback only every N-th exchange.
"""

from app.bot.handlers.chat import (
    _FEEDBACK_EVERY_N,
    _friendly_exchange_count,
    _friendly_reply_keyboard,
)


def _reset_count(user_id: int) -> None:
    _friendly_exchange_count.pop(user_id, None)


class TestFriendlyReplyKeyboard:
    USER_ID = 99001

    def setup_method(self):
        _reset_count(self.USER_ID)

    def test_first_turn_returns_none(self):
        kb = _friendly_reply_keyboard(self.USER_ID, "ru")
        assert kb is None, "First turn should have no inline keyboard"

    def test_most_turns_return_none(self):
        nones = []
        for _ in range(_FEEDBACK_EVERY_N - 1):
            kb = _friendly_reply_keyboard(self.USER_ID, "ru")
            nones.append(kb)
        assert all(k is None for k in nones), "All pre-feedback turns should be None"

    def test_nth_turn_returns_feedback_keyboard(self):
        for _ in range(_FEEDBACK_EVERY_N - 1):
            _friendly_reply_keyboard(self.USER_ID, "ru")
        kb = _friendly_reply_keyboard(self.USER_ID, "ru")
        assert kb is not None, f"Turn {_FEEDBACK_EVERY_N} must return feedback keyboard"

    def test_cycle_repeats(self):
        # First cycle: feedback on turn N
        for _ in range(_FEEDBACK_EVERY_N):
            kb = _friendly_reply_keyboard(self.USER_ID, "ru")
        assert kb is not None

        # Second cycle: None again immediately after
        kb = _friendly_reply_keyboard(self.USER_ID, "ru")
        assert kb is None

    def test_feedback_keyboard_has_helpful_buttons(self):
        for _ in range(_FEEDBACK_EVERY_N):
            kb = _friendly_reply_keyboard(self.USER_ID, "ru")
        assert kb is not None
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        callback_data_values = {b.callback_data for b in all_buttons}
        assert "fbk_y" in callback_data_values
        assert "fbk_n" in callback_data_values

    def test_different_users_are_independent(self):
        user_a = 99002
        user_b = 99003
        _reset_count(user_a)
        _reset_count(user_b)

        # Advance user_a to N-1 turns
        for _ in range(_FEEDBACK_EVERY_N - 1):
            _friendly_reply_keyboard(user_a, "ru")

        # user_b should still be on turn 1 → None
        kb_b = _friendly_reply_keyboard(user_b, "ru")
        assert kb_b is None

        # user_a next turn → feedback
        kb_a = _friendly_reply_keyboard(user_a, "ru")
        assert kb_a is not None
