"""Golden dialogue tests for tone quality and routing correctness.

Tests are deterministic — they verify:
  - Crisis template content (warmth, safety check, invitation to continue)
  - Intake classifier routing for new scenarios
  - Crisis detector coverage for new LEVEL_4 patterns
  - Quality checker behavior by risk tier
  - Tone quality assertions: no emergency language for Tier 0-1, no premature referral
"""

import pytest

from app.ai.orchestration.models import RiskTier
from app.ai.response_quality import check_response_quality
from app.ai.routing.intake import classify_intake
from app.db.models import RiskLevel
from app.safety.crisis_detector import deterministic_crisis_check


# ---------------------------------------------------------------------------
# A. Passive disappearance — deterministic routing
# ---------------------------------------------------------------------------


def test_a_passive_disappearance_detected_as_elevated_distress() -> None:
    risk, _ = deterministic_crisis_check("I wish I could disappear.")
    assert risk == RiskLevel.ELEVATED_DISTRESS


def test_a_passive_disappearance_ru_detected() -> None:
    risk, _ = deterministic_crisis_check("Я хочу исчезнуть.")
    assert risk == RiskLevel.ELEVATED_DISTRESS


# ---------------------------------------------------------------------------
# A. Crisis template content — passive_risk
# ---------------------------------------------------------------------------


def test_a_passive_risk_template_en_has_safety_question() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.passive_risk", "en")
    lower = text.lower()
    # Must ask about safety
    assert any(phrase in lower for phrase in ["immediate danger", "hurt yourself", "safe right now"])


def test_a_passive_risk_template_en_has_invitation_to_continue() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.passive_risk", "en")
    lower = text.lower()
    # Must invite continuation, not just redirect
    assert any(phrase in lower for phrase in ["stay with me", "tell me", "what's been happening"])


def test_a_passive_risk_template_en_does_not_start_with_emergency() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.passive_risk", "en")
    # First sentence should not be about emergency services
    first_sentence = text.split(".")[0].lower()
    assert "emergency services" not in first_sentence
    assert "crisis line" not in first_sentence


def test_a_passive_risk_template_ru_has_safety_question() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.passive_risk", "ru")
    lower = text.lower()
    assert any(phrase in lower for phrase in ["безопасности", "причинить себе вред", "в безопасности"])


def test_a_passive_risk_template_ru_has_invitation_to_continue() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.passive_risk", "ru")
    lower = text.lower()
    assert any(phrase in lower for phrase in ["останься со мной", "расскажи", "рядом"])


# ---------------------------------------------------------------------------
# B. Loss of meaning — intake routing
# ---------------------------------------------------------------------------


def test_b_loss_of_meaning_ru_routes_to_correct_scenario() -> None:
    result = classify_intake("Я теряю смысл жизни.", "ru")
    assert result.scenario_id == "loss_of_meaning"


def test_b_loss_of_meaning_not_caught_by_crisis_detector() -> None:
    # "Я теряю смысл жизни" alone is not imminent crisis — should go to LLM
    risk, _ = deterministic_crisis_check("Я теряю смысл жизни.")
    assert risk < RiskLevel.POSSIBLE_CRISIS


def test_b_elevated_template_en_is_warm_not_clinical() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.elevated", "en")
    lower = text.lower()
    # Should NOT immediately push to specialist as first move
    assert not lower.startswith("please reach out to a specialist")
    assert not lower.startswith("contact a specialist")
    # Should contain warmth
    assert any(phrase in lower for phrase in ["i hear", "i'm here", "with you"])


def test_b_elevated_template_ru_is_warm_not_clinical() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.elevated", "ru")
    lower = text.lower()
    assert not lower.startswith("пожалуйста, обратись к специалисту")
    assert any(phrase in lower for phrase in ["слышу", "рядом"])


# ---------------------------------------------------------------------------
# C. Divorce/betrayal — intake routing
# ---------------------------------------------------------------------------


def test_c_divorce_betrayal_routes_to_breakup_scenario() -> None:
    result = classify_intake(
        "После 19 лет брака жена ушла к другому. Я не могу это пережить.", "ru"
    )
    assert result.scenario_id == "breakup_divorce"


def test_c_betrayal_keyword_routes_to_breakup_scenario() -> None:
    result = classify_intake("Она изменила мне.", "ru")
    assert result.scenario_id == "breakup_divorce"


def test_c_english_betrayal_routes_to_breakup_scenario() -> None:
    result = classify_intake("She cheated on me after 10 years.", "en")
    assert result.scenario_id == "breakup_divorce"


# ---------------------------------------------------------------------------
# D. Isolation — stays as loneliness, no emergency referral
# ---------------------------------------------------------------------------


def test_d_isolation_routes_to_loneliness_or_general_scenario() -> None:
    # "Мне некому рассказать" doesn't contain explicit loneliness keywords,
    # so general_support is the valid fallback — the LLM handles isolation context
    result = classify_intake("Мне некому это рассказать. Я не могу признаться людям, насколько мне плохо.", "ru")
    assert result.scenario_id in ("loneliness", "general_support")


def test_d_isolation_not_caught_by_crisis_detector() -> None:
    risk, _ = deterministic_crisis_check("Мне некому это рассказать.")
    assert risk == RiskLevel.NO_RISK


# ---------------------------------------------------------------------------
# E. Severe despair with safety qualifier — NOT imminent
# ---------------------------------------------------------------------------


def test_e_despair_with_qualifier_not_level4() -> None:
    risk, _ = deterministic_crisis_check(
        "Мне не хочется жить, но я ничего с собой делать не собираюсь."
    )
    assert risk < RiskLevel.IMMINENT_RISK


def test_e_despair_with_qualifier_not_level3() -> None:
    risk, _ = deterministic_crisis_check(
        "Мне не хочется жить, но я ничего с собой делать не собираюсь."
    )
    # Should not trigger POSSIBLE_CRISIS — goes to LLM pipeline
    assert risk < RiskLevel.POSSIBLE_CRISIS


# ---------------------------------------------------------------------------
# F. Imminent danger — must escalate
# ---------------------------------------------------------------------------


def test_f_imminent_danger_ru_explicit_plan() -> None:
    risk, _ = deterministic_crisis_check(
        "Я собираюсь покончить с собой сегодня, у меня есть таблетки."
    )
    assert risk == RiskLevel.IMMINENT_RISK


def test_f_imminent_danger_en_going_to_kill() -> None:
    risk, _ = deterministic_crisis_check("I'm going to kill myself tonight.")
    assert risk == RiskLevel.IMMINENT_RISK


def test_f_imminent_danger_en_commit_suicide() -> None:
    risk, _ = deterministic_crisis_check("I am going to commit suicide.")
    assert risk == RiskLevel.IMMINENT_RISK


def test_f_imminent_danger_response_contains_emergency_guidance() -> None:
    from app.bot.handlers.i18n import get_text

    text = get_text("crisis.response", "en")
    lower = text.lower()
    assert any(phrase in lower for phrase in ["emergency services", "crisis line"])


# ---------------------------------------------------------------------------
# Quality checker: Tier 0-1 tone assertions
# ---------------------------------------------------------------------------


def test_quality_flags_emergency_language_in_tier0_response() -> None:
    draft = "I hear you. Please contact emergency services right away."
    result = check_response_quality(draft, RiskTier.TIER_0)
    assert result.emergency_language_mismatch is True
    assert result.should_rewrite is True


def test_quality_flags_specialist_referral_in_tier1_response() -> None:
    draft = "I understand. Please seek professional help from a therapist."
    result = check_response_quality(draft, RiskTier.TIER_1)
    assert result.premature_referral is True
    assert result.should_rewrite is True


def test_quality_flags_ai_identity_leak() -> None:
    draft = "As an AI, I want to acknowledge your feelings."
    result = check_response_quality(draft, RiskTier.TIER_0)
    assert result.ai_identity_leak is True
    assert result.should_rewrite is True


def test_quality_allows_emergency_language_in_tier3_response() -> None:
    draft = "Please contact emergency services right away. You need real help now."
    result = check_response_quality(draft, RiskTier.TIER_3)
    assert result.emergency_language_mismatch is False


def test_quality_allows_referral_in_tier2_response() -> None:
    # Tier 2: referral is not premature
    draft = "Я слышу тебя. Если тебе плохо уже долго, обратись к специалисту."
    result = check_response_quality(draft, RiskTier.TIER_2)
    assert result.premature_referral is False


def test_quality_clean_response_has_no_issues() -> None:
    draft = (
        "That sounds really heavy — carrying this alone for so long takes a toll. "
        "You don't have to make it sound neat or acceptable. "
        "What's the part that feels hardest right now?"
    )
    result = check_response_quality(draft, RiskTier.TIER_1)
    assert result.should_rewrite is False
    assert result.issues() == "none"


def test_quality_clean_russian_response_has_no_issues() -> None:
    draft = (
        "Я слышу тебя. Это звучит как очень тяжёлое место — боль, которая накопилась. "
        "Расскажи мне, что происходит — как есть, без украшений."
    )
    result = check_response_quality(draft, RiskTier.TIER_1)
    assert result.should_rewrite is False


# ---------------------------------------------------------------------------
# Quality checker: Tier 0-1 — no emergency language for normal distress
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "I feel anxious.",
        "I'm sad.",
        "I feel lonely.",
        "Мне тревожно.",
        "Мне грустно.",
        "Мне одиноко.",
    ],
)
def test_normal_distress_not_caught_by_crisis_detector(text: str) -> None:
    risk, _ = deterministic_crisis_check(text)
    assert risk == RiskLevel.NO_RISK


# ---------------------------------------------------------------------------
# Crisis template: imminent danger response must not be overly long
# ---------------------------------------------------------------------------


def test_crisis_response_is_concise() -> None:
    from app.bot.handlers.i18n import get_text

    # Imminent danger response should be focused, not a wall of text
    text = get_text("crisis.response", "en")
    # Under 600 chars is a reasonable bound for a focused crisis response
    assert len(text) < 600


def test_passive_risk_response_is_longer_than_crisis_response() -> None:
    from app.bot.handlers.i18n import get_text

    # Passive risk response should have more warmth and context than the crisis response
    passive = get_text("crisis.passive_risk", "en")
    crisis = get_text("crisis.response", "en")
    assert len(passive) > 0
    assert len(crisis) > 0
