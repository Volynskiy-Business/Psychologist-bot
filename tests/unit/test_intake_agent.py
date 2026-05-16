"""Tests for the deterministic intake agent."""


from app.ai.orchestration.models import RiskTier
from app.ai.routing.intake import classify_intake, detect_language


# ── Language detection ─────────────────────────────────────────────────────

def test_detect_language_russian():
    assert detect_language("Мне очень грустно сегодня") == "ru"


def test_detect_language_english():
    assert detect_language("I feel very anxious today") == "en"


def test_detect_language_cyrillic_heavy():
    assert detect_language("грустно и тяжело мне") == "ru"


def test_detect_language_mixed_prefers_cyrillic():
    # Cyrillic > 30% of alpha chars → Russian
    assert detect_language("Привет I am sad") == "ru"


def test_detect_language_empty_defaults_to_ru():
    assert detect_language("") == "ru"


# ── Scenario detection ─────────────────────────────────────────────────────

def test_classify_sadness_scenario():
    result = classify_intake("мне грустно и тоскливо")
    assert result.scenario_id == "sadness_grief"
    assert result.detected_emotion == "sadness"


def test_classify_anxiety_scenario():
    result = classify_intake("я очень тревожусь и беспокоюсь")
    assert result.scenario_id == "anxiety"
    assert result.detected_emotion == "anxiety"


def test_classify_anger_scenario():
    result = classify_intake("меня это бесит и злит")
    assert result.scenario_id == "anger"
    assert result.detected_emotion == "anger"


def test_classify_loneliness_scenario():
    result = classify_intake("я чувствую одиночество, никто не понимает")
    assert result.scenario_id == "loneliness"
    assert result.detected_emotion == "loneliness"


def test_classify_exhaustion_scenario():
    result = classify_intake("я очень устал, нет сил совсем")
    assert result.scenario_id == "exhaustion"
    assert result.detected_emotion == "exhaustion"


def test_classify_guilt_shame_scenario():
    result = classify_intake("я чувствую вину и стыд")
    assert result.scenario_id == "guilt_shame"
    assert result.detected_emotion == "guilt"


def test_classify_loss_of_meaning_scenario():
    result = classify_intake("нет смысла, всё апатично и безразлично")
    assert result.scenario_id == "loss_of_meaning"
    assert result.detected_emotion == "loss_of_meaning"


def test_classify_uncertainty_scenario():
    result = classify_intake("я потерялся, не знаю что делать, хаос")
    assert result.scenario_id == "uncertainty"
    assert result.detected_emotion == "uncertainty"


def test_classify_english_anxiety():
    result = classify_intake("I feel very anxious and worried all the time")
    assert result.scenario_id == "anxiety"
    assert result.language == "en"


def test_classify_english_sadness():
    result = classify_intake("I am very sad and feeling grief")
    assert result.scenario_id == "sadness_grief"


def test_classify_general_fallback():
    result = classify_intake("привет, как дела")
    assert result.scenario_id == "general_support"
    assert result.detected_emotion == "general"


# ── Intensity ──────────────────────────────────────────────────────────────

def test_intensity_boosted_by_modifiers():
    low = classify_intake("мне грустно")
    high = classify_intake("мне очень грустно и ужасно тяжело")
    assert high.intensity >= low.intensity


def test_intensity_within_bounds():
    result = classify_intake("мне очень очень очень очень плохо")
    assert 0.0 <= result.intensity <= 1.0


# ── Risk tier ─────────────────────────────────────────────────────────────

def test_risk_tier_0_for_no_distress():
    result = classify_intake("привет, расскажи мне о погоде")
    assert result.risk_tier == RiskTier.TIER_0


def test_risk_tier_1_for_emotional_distress():
    result = classify_intake("мне грустно")
    assert result.risk_tier == RiskTier.TIER_1


def test_risk_tier_2_for_hopelessness_signal():
    result = classify_intake("нет смысла жить, я больше не могу жить так")
    assert result.risk_tier == RiskTier.TIER_2
    assert len(result.risk_signals) > 0


def test_risk_tier_2_for_english_hopelessness():
    result = classify_intake("I have no reason to live anymore")
    assert result.risk_tier == RiskTier.TIER_2


def test_risk_signals_populated_when_detected():
    result = classify_intake("устала жить, никому не нужна")
    assert result.risk_tier == RiskTier.TIER_2
    assert len(result.risk_signals) >= 1


def test_death_of_loved_one_en_not_misrouted_as_breakup():
    """English death message must route to death_of_loved_one, not breakup_divorce."""
    result = classify_intake("My mother died and I don't know how to live now")
    assert result.scenario_id != "breakup_divorce", (
        "Death of a loved one misrouted as breakup_divorce"
    )
    assert result.scenario_id in ("death_of_loved_one", "sadness_grief", "loss_of_meaning")


def test_english_passive_disappearance_is_tier2():
    """English passive disappearance wish must trigger Tier 2 safety awareness."""
    result = classify_intake("I just want to disappear and not exist anymore")
    assert result.risk_tier == RiskTier.TIER_2


# ── Fraud routing — negative cases (no false positives on savings talk) ────

def test_savings_alone_does_not_route_to_fraud_trauma():
    """Generic savings mention without fraud context must not trigger financial_fraud_trauma."""
    result = classify_intake("I'm worried about my savings because of inflation.")
    assert result.scenario_id != "financial_fraud_trauma"


def test_save_money_does_not_route_to_fraud_trauma():
    result = classify_intake("I want to save money for the future.")
    assert result.scenario_id != "financial_fraud_trauma"


def test_anxious_about_saving_does_not_route_to_fraud_trauma():
    result = classify_intake("I'm anxious about saving for retirement.")
    assert result.scenario_id != "financial_fraud_trauma"


def test_fraud_with_scammed_routes_correctly():
    """Explicit fraud signal + savings still routes to financial_fraud_trauma."""
    result = classify_intake("I got scammed and lost all my savings.")
    assert result.scenario_id == "financial_fraud_trauma"
