"""Tests for technique library completeness, structure, and constraints."""


from app.ai.techniques.loader import get_all_techniques, get_technique, select_technique
from app.ai.scenarios.loader import get_scenario

REQUIRED_TECHNIQUE_IDS = {
    "labeling_dbt", "self_compassion_neff", "behavioral_activation",
    "permission_to_grieve", "physiological_sigh", "grounding_54321",
    "worry_scheduling", "accepting_uncertainty_act",
    "physical_discharge", "stop_pause", "validate_need", "i_statement_nvc",
    "micro_contact", "common_humanity_act", "mindful_self_presence",
    "minimum_dose", "check_basic_needs", "resource_inventory",
    "letter_to_friend_cbt", "guilt_vs_shame", "reparative_action",
    "normalize_apathy", "values_compass_act", "action_without_motivation",
    "circles_of_influence", "next_small_step", "body_grounding",
}


def test_all_techniques_load_without_error():
    techniques = get_all_techniques()
    assert len(techniques) > 0


def test_no_duplicate_technique_ids():
    ids = [t.id for t in get_all_techniques()]
    assert len(ids) == len(set(ids)), (
        f"Duplicate technique IDs: {[i for i in ids if ids.count(i) > 1]}"
    )


def test_expected_technique_ids_present():
    ids = {t.id for t in get_all_techniques()}
    missing = REQUIRED_TECHNIQUE_IDS - ids
    assert not missing, f"Missing expected techniques: {missing}"


def test_all_techniques_have_non_empty_required_fields():
    for technique in get_all_techniques():
        assert technique.id.strip(), "Technique has empty id"
        assert technique.title.strip(), f"Technique '{technique.id}' has empty title"
        assert technique.evidence_base.strip(), f"Technique '{technique.id}' has empty evidence_base"
        assert technique.instructions.strip(), f"Technique '{technique.id}' has empty instructions"


def test_risk_ceiling_is_valid_tier():
    for technique in get_all_techniques():
        assert 0 <= technique.risk_ceiling <= 4, (
            f"Technique '{technique.id}' has invalid risk_ceiling: {technique.risk_ceiling}"
        )


def test_emotion_states_non_empty():
    for technique in get_all_techniques():
        assert len(technique.emotion_states) > 0, (
            f"Technique '{technique.id}' has no emotion_states"
        )


def test_get_technique_returns_none_for_unknown_id():
    assert get_technique("nonexistent_technique_xyz") is None


# ── select_technique ──────────────────────────────────────────────────────

def test_select_technique_returns_first_safe_for_tier1():
    scenario = get_scenario("sadness_grief")
    technique = select_technique(scenario, risk_tier=1)
    assert technique is not None
    assert technique.id == "labeling_dbt"  # first in the list with risk_ceiling >= 1


def test_select_technique_skips_techniques_above_risk_ceiling():
    scenario = get_scenario("sadness_grief")
    # behavioral_activation has risk_ceiling=1, so at tier 2 it should be skipped
    technique = select_technique(scenario, risk_tier=2)
    assert technique is not None
    # labeling_dbt (risk_ceiling=2) should be selected instead
    assert technique.id == "labeling_dbt"


def test_select_technique_returns_none_for_no_scenario():
    result = select_technique(None, risk_tier=1)
    assert result is None


def test_select_technique_returns_none_when_no_techniques_in_scenario():
    scenario = get_scenario("diagnosis_request")
    result = select_technique(scenario, risk_tier=1)
    assert result is None


def test_select_technique_grounding_available_at_tier2():
    scenario = get_scenario("anxiety")
    # physiological_sigh has risk_ceiling=2 — should be selected at tier 2
    technique = select_technique(scenario, risk_tier=2)
    assert technique is not None
    assert technique.risk_ceiling >= 2


def test_high_risk_ceiling_technique_available_at_tier3():
    scenario = get_scenario("uncertainty")
    # body_grounding has risk_ceiling=3 — available at tier 3
    technique = select_technique(scenario, risk_tier=3)
    assert technique is not None
    assert technique.risk_ceiling >= 3


def test_all_techniques_have_bot_usage_boundary():
    for technique in get_all_techniques():
        assert technique.bot_usage_boundary is not None, (
            f"Technique '{technique.id}' has no bot_usage_boundary"
        )
        assert technique.bot_usage_boundary.strip(), (
            f"Technique '{technique.id}' has empty bot_usage_boundary"
        )
