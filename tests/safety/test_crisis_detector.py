"""Tests for crisis detector."""

import pytest

from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check


@pytest.mark.parametrize(
    "text,expected_level",
    [
        ("Я хочу умереть", RiskLevel.IMMINENT_RISK),
        ("У меня есть план покончить с собой", RiskLevel.IMMINENT_RISK),
        ("Я выпил таблеток", RiskLevel.IMMINENT_RISK),
        ("Не хочу жить", RiskLevel.POSSIBLE_CRISIS),
        ("Мне грустно", RiskLevel.NO_RISK),
        ("Я прокрастинирую", RiskLevel.NO_RISK),
    ],
)
def test_crisis_detection(text: str, expected_level: RiskLevel) -> None:
    level, _ = deterministic_crisis_check(text)
    assert level == expected_level


@pytest.mark.parametrize(
    "text",
    [
        # English — exact phrases from task specification
        "I wish I could disappear.",
        "I want to disappear",
        "I wish I wasn't here",
        "I don't want to exist",
        "I want to vanish",
        "I want to be gone",
        "I don't want to wake up",
        # English — natural variations
        "sometimes I just want to disappear",
        "I wish I could just disappear forever",
        "I feel like I want to vanish",
        "I don't want to wake up tomorrow",
        # Russian
        "хочу исчезнуть",
        "я хочу исчезнуть",
        "не хочу существовать",
        "не хочу просыпаться",
        "хочу пропасть",
        "лучше бы меня не было",
        "желаю исчезнуть",
    ],
)
def test_passive_disappearance_signals_detected_as_elevated_distress(text: str) -> None:
    level, pattern = deterministic_crisis_check(text)
    assert level == RiskLevel.ELEVATED_DISTRESS, (
        f"Expected ELEVATED_DISTRESS for {text!r}, got {level!r} (pattern={pattern!r})"
    )


@pytest.mark.parametrize(
    "text",
    [
        # Normal support phrases must NOT trigger L2
        "I feel anxious",
        "I'm sad today",
        "I broke up with someone and it hurts",
        "I'm having a hard week",
        "мне грустно",
        "я устал",
        "тревожно",
    ],
)
def test_normal_distress_not_flagged_as_elevated_distress(text: str) -> None:
    level, _ = deterministic_crisis_check(text)
    assert level != RiskLevel.ELEVATED_DISTRESS, (
        f"Normal phrase {text!r} incorrectly flagged as ELEVATED_DISTRESS"
    )
