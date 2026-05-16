"""Tests for scenario library completeness, structure, and referential integrity."""


from app.ai.scenarios.loader import get_all_scenarios, get_scenario
from app.ai.techniques.loader import get_all_techniques

REQUIRED_FIELDS = {
    "id", "title", "emotion_signals", "risk_signals", "risk_ceiling",
    "recommended_techniques", "response_shape", "do_rules", "dont_rules",
    "contraindications", "escalation_rules",
}

EXPECTED_SCENARIO_IDS = {
    "sadness_grief", "anxiety", "anger", "loneliness", "exhaustion",
    "guilt_shame", "loss_of_meaning", "uncertainty",
    "diagnosis_request", "medication_question", "general_support",
    "breakup_divorce", "death_of_loved_one", "job_loss", "financial_loss",
    "serious_illness_or_disability", "passive_death_thoughts",
    "possible_self_harm", "imminent_danger",
}


def test_all_scenarios_load_without_error():
    scenarios = get_all_scenarios()
    assert len(scenarios) > 0


def test_no_duplicate_scenario_ids():
    ids = [s.id for s in get_all_scenarios()]
    assert len(ids) == len(set(ids)), f"Duplicate scenario IDs: {[i for i in ids if ids.count(i) > 1]}"


def test_expected_scenario_ids_present():
    ids = {s.id for s in get_all_scenarios()}
    missing = EXPECTED_SCENARIO_IDS - ids
    assert not missing, f"Missing expected scenarios: {missing}"


def test_general_support_is_fallback_present():
    scenario = get_scenario("general_support")
    assert scenario is not None


def test_all_scenarios_have_required_fields():
    for scenario in get_all_scenarios():
        scenario_dict = scenario.model_dump()
        for field in REQUIRED_FIELDS:
            assert field in scenario_dict, f"Scenario '{scenario.id}' missing field '{field}'"


def test_all_scenarios_have_non_empty_id_and_title():
    for scenario in get_all_scenarios():
        assert scenario.id.strip(), "Scenario has empty id"
        assert scenario.title.strip(), f"Scenario '{scenario.id}' has empty title"


def test_all_scenarios_have_response_shape():
    for scenario in get_all_scenarios():
        assert scenario.response_shape.strip(), f"Scenario '{scenario.id}' has empty response_shape"


def test_risk_ceiling_is_valid_tier():
    for scenario in get_all_scenarios():
        assert 0 <= scenario.risk_ceiling <= 4, (
            f"Scenario '{scenario.id}' has invalid risk_ceiling: {scenario.risk_ceiling}"
        )


def test_all_recommended_techniques_exist_in_technique_library():
    technique_ids = {t.id for t in get_all_techniques()}
    for scenario in get_all_scenarios():
        for tid in scenario.recommended_techniques:
            assert tid in technique_ids, (
                f"Scenario '{scenario.id}' references unknown technique '{tid}'"
            )


def test_scenarios_without_techniques_are_valid():
    # diagnosis_request and medication_question intentionally have no techniques
    for scenario_id in ("diagnosis_request", "medication_question"):
        scenario = get_scenario(scenario_id)
        assert scenario is not None
        assert scenario.recommended_techniques == []


def test_get_scenario_returns_none_for_unknown_id():
    assert get_scenario("nonexistent_scenario_xyz") is None
