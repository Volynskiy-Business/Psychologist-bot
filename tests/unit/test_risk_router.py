"""Tests for risk tier routing via the intake agent."""


from app.ai.orchestration.models import RiskTier
from app.ai.routing.intake import _detect_risk_tier, classify_intake


# ── Direct _detect_risk_tier tests ────────────────────────────────────────

def test_tier0_when_no_signals_and_general_scenario():
    tier, signals = _detect_risk_tier("привет", "general_support", [])
    assert tier == RiskTier.TIER_0
    assert signals == []


def test_tier1_when_no_risk_signals_but_specific_scenario():
    tier, signals = _detect_risk_tier("я тревожусь", "anxiety", [])
    assert tier == RiskTier.TIER_1
    assert signals == []


def test_tier2_on_global_hopelessness_signal():
    tier, signals = _detect_risk_tier("нет смысла жить", "sadness_grief", [])
    assert tier == RiskTier.TIER_2
    assert "нет смысла жить" in signals


def test_tier2_on_scenario_specific_signal():
    tier, signals = _detect_risk_tier(
        "никому не нужен", "loneliness", ["никому не нужен", "зачем жить"]
    )
    assert tier == RiskTier.TIER_2
    assert "никому не нужен" in signals


def test_tier2_on_english_signal():
    tier, signals = _detect_risk_tier("I have no reason to live", "sadness_grief", [])
    assert tier == RiskTier.TIER_2


def test_signals_deduplicated_between_global_and_scenario():
    # "нет смысла жить" appears in both global list and scenario risk_signals
    tier, signals = _detect_risk_tier(
        "нет смысла жить", "sadness_grief", ["нет смысла жить"]
    )
    assert tier == RiskTier.TIER_2
    # Should not duplicate the same signal
    assert signals.count("нет смысла жить") == 1


# ── Integration: crisis override via classify_intake ──────────────────────

def test_crisis_override_takes_precedence_over_scenario():
    result = classify_intake("мне грустно и нет смысла жить")
    assert result.risk_tier == RiskTier.TIER_2
    # Scenario may still be sadness, but risk overrides to Tier 2
    assert result.risk_signals


def test_ordinary_message_no_risk_signals():
    result = classify_intake("мне немного грустно сегодня")
    assert result.risk_tier in (RiskTier.TIER_0, RiskTier.TIER_1)
    assert result.risk_signals == []
