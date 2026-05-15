"""Deterministic intake agent.

Classifies incoming user messages into structured IntakeResult metadata
without any LLM calls, using keyword scoring against the scenario library.
"""

import re
from typing import Optional

from app.ai.orchestration.models import IntakeResult, RiskTier
from app.ai.scenarios.loader import get_all_scenarios

# Signals that indicate Tier 2: elevated distress, hopelessness, severe isolation.
# Tier 3/4 are caught upstream by the deterministic crisis detector before the pipeline.
_TIER_2_SIGNALS: list[str] = [
    # Russian
    "невыносимо",
    "больше не могу жить",
    "нет смысла жить",
    "устал жить",
    "устала жить",
    "никому не нужен",
    "никому не нужна",
    "зачем жить",
    "зачем мне жить",
    "не хочу просыпаться",
    "лучше бы меня не было",
    "не заслуживаю жить",
    # Russian — passive disappearance wishes
    "хочу исчезнуть",
    "желаю исчезнуть",
    "не хочу существовать",
    # English
    "no reason to live",
    "not worth living",
    "tired of living",
    "nobody needs me",
    "better off dead",
    "can't go on",
    "no point in living",
    "want to disappear",
    "wish i wasn't here",
    "wish i didn't exist",
]

# Intensity modifier words — boost calculated intensity score.
_INTENSITY_BOOSTERS: list[str] = [
    "очень", "крайне", "невыносимо", "ужасно", "совсем", "сильно",
    "очень сильно", "дико", "жутко",
    "very", "extremely", "terribly", "so", "really", "incredibly",
]


def detect_language(text: str) -> str:
    """Heuristic language detection based on script proportion."""
    cyrillic = len(re.findall(r"[а-яёА-ЯЁ]", text))
    total_alpha = len(re.findall(r"[a-zA-Zа-яёА-ЯЁ]", text))
    if total_alpha == 0:
        return "ru"
    if cyrillic / total_alpha > 0.3:
        ukrainian = len(re.findall(r"[іїєґІЇЄҐ]", text))
        if ukrainian > 2:
            return "uk"
        return "ru"
    return "en"


def _score_scenario(signals: list[str], text_lower: str) -> int:
    return sum(1 for signal in signals if signal.lower() in text_lower)


def _detect_scenario(text: str) -> tuple[str, str, float]:
    """Return (detected_emotion, scenario_id, intensity)."""
    text_lower = text.lower()
    scenarios = get_all_scenarios()

    best_scenario = None
    best_score = 0

    # Special-case scenarios that should only match on strong explicit signals.
    priority_ids = {"diagnosis_request", "medication_question"}

    for scenario in scenarios:
        if scenario.id == "general_support":
            continue  # evaluated last as fallback
        score = _score_scenario(scenario.emotion_signals, text_lower)
        # Require at least 2 matches for priority scenarios to avoid false positives.
        if scenario.id in priority_ids and score < 2:
            continue
        if score > best_score:
            best_score = score
            best_scenario = scenario

    if best_scenario is None or best_score == 0:
        best_scenario = next(s for s in scenarios if s.id == "general_support")

    _EMOTION_MAP: dict[str, str] = {
        "sadness_grief": "sadness",
        "anxiety": "anxiety",
        "anger": "anger",
        "loneliness": "loneliness",
        "exhaustion": "exhaustion",
        "guilt_shame": "guilt",
        "loss_of_meaning": "loss_of_meaning",
        "uncertainty": "uncertainty",
        "diagnosis_request": "diagnosis_request",
        "medication_question": "medication_question",
        "general_support": "general",
        "breakup_divorce": "sadness",
        "death_of_loved_one": "grief",
        "job_loss": "loss_of_meaning",
        "financial_loss": "anxiety",
        "serious_illness_or_disability": "uncertainty",
        "passive_death_thoughts": "passive_death_thoughts",
        "possible_self_harm": "possible_self_harm",
        "imminent_danger": "imminent_danger",
    }
    detected_emotion = _EMOTION_MAP.get(best_scenario.id, "general")

    booster_count = sum(1 for b in _INTENSITY_BOOSTERS if b in text_lower)
    intensity = min(0.3 + best_score * 0.15 + booster_count * 0.1, 1.0)

    return detected_emotion, best_scenario.id, intensity


def _detect_risk_tier(
    text: str,
    scenario_id: str,
    scenario_risk_signals: Optional[list[str]] = None,
) -> tuple[RiskTier, list[str]]:
    """Return (RiskTier, matched_signals).

    Tier 3/4 are handled upstream — this function only determines Tier 0–2.
    """
    text_lower = text.lower()
    matched: list[str] = []

    # Global Tier 2 signals
    for signal in _TIER_2_SIGNALS:
        if signal in text_lower:
            matched.append(signal)

    # Per-scenario risk signals
    if scenario_risk_signals:
        for signal in scenario_risk_signals:
            if signal.lower() in text_lower and signal not in matched:
                matched.append(signal)

    if matched:
        return RiskTier.TIER_2, matched

    # Tier 1: any specific emotional scenario was matched
    if scenario_id != "general_support":
        return RiskTier.TIER_1, []

    return RiskTier.TIER_0, []


def classify_intake(text: str, lang: str = "") -> IntakeResult:
    """Full intake classification — deterministic, no LLM calls."""
    if not lang:
        lang = detect_language(text)

    detected_emotion, scenario_id, intensity = _detect_scenario(text)

    # Get scenario-specific risk signals for the matched scenario
    from app.ai.scenarios.loader import get_scenario  # local to avoid top-level circular
    scenario = get_scenario(scenario_id)
    scenario_risk_signals = scenario.risk_signals if scenario else []

    risk_tier, risk_signals = _detect_risk_tier(text, scenario_id, scenario_risk_signals)

    return IntakeResult(
        language=lang,
        detected_emotion=detected_emotion,
        intensity=intensity,
        scenario_id=scenario_id,
        risk_tier=risk_tier,
        risk_signals=risk_signals,
    )
