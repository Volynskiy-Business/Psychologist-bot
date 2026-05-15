"""Tests for support agent prompt safety invariants."""

from app.ai.orchestration.models import IntakeResult, RiskTier
from app.ai.prompts.support_agent_prompt import build_support_prompt
from app.ai.scenarios.loader import get_scenario
from app.ai.techniques.loader import get_technique


def _make_intake(scenario_id: str = "sadness_grief", risk_tier: int = 1) -> IntakeResult:
    return IntakeResult(
        language="ru",
        detected_emotion="sadness",
        intensity=0.5,
        scenario_id=scenario_id,
        risk_tier=RiskTier(risk_tier),
        risk_signals=[],
    )


def _base_prompt() -> str:
    return build_support_prompt(_make_intake(), scenario=None, technique=None)


def _full_prompt(scenario_id: str = "sadness_grief", risk_tier: int = 1) -> str:
    intake = _make_intake(scenario_id, risk_tier)
    scenario = get_scenario(scenario_id)
    technique = get_technique("labeling_dbt") if scenario and scenario.recommended_techniques else None
    return build_support_prompt(intake, scenario, technique)


# ── Role boundary ─────────────────────────────────────────────────────────────

def test_prompt_explicitly_disclaims_doctor_role():
    prompt = _base_prompt()
    assert "не врач" in prompt


def test_prompt_explicitly_disclaims_therapist_role():
    prompt = _base_prompt()
    assert "психотерапевт" in prompt


def test_prompt_does_not_claim_clinical_role():
    prompt = _base_prompt()
    forbidden_claims = [
        "Я ваш терапевт",
        "Я твой психолог",
        "Я клинический",
        "I am your therapist",
        "I am a doctor",
    ]
    for claim in forbidden_claims:
        assert claim.lower() not in prompt.lower(), f"Forbidden claim found: '{claim}'"


# ── Prohibited content ────────────────────────────────────────────────────────

def test_prompt_prohibits_diagnosis():
    prompt = _base_prompt()
    assert "диагноз" in prompt.lower() or "Не ставь" in prompt


def test_prompt_prohibits_medication_advice():
    prompt = _base_prompt()
    assert "лекарства" in prompt.lower() or "дозировк" in prompt.lower()


def test_prompt_prohibits_outcome_promises():
    prompt = _base_prompt()
    assert "не обещай" in prompt.lower() or "не обеща" in prompt.lower()


def test_prompt_prohibits_self_harm_instructions():
    prompt = _base_prompt()
    assert "самоповреждению" in prompt.lower() or "суициду" in prompt.lower()


# ── Anti-dependency ───────────────────────────────────────────────────────────

def test_prompt_discourages_bot_dependency():
    prompt = _base_prompt()
    assert "зависимость" in prompt.lower() or "живого общения" in prompt.lower()


# ── Formatting rules ──────────────────────────────────────────────────────────

def test_prompt_prohibits_markdown_formatting():
    prompt = _base_prompt()
    assert "Markdown" in prompt or "жирных" in prompt or "markdown" in prompt.lower()


def test_prompt_limits_response_length():
    prompt = _base_prompt()
    assert "предложени" in prompt.lower() or "4–8" in prompt or "4-8" in prompt


def test_prompt_limits_to_one_question():
    prompt = _base_prompt()
    assert "один вопрос" in prompt.lower() or "одного вопроса" in prompt.lower()


def test_prompt_limits_to_one_technique():
    prompt = _base_prompt()
    assert "одной техники" in prompt.lower() or "одну технику" in prompt.lower() or "одна техника" in prompt.lower() or "не более одной" in prompt.lower()


# ── Crisis section always present ─────────────────────────────────────────────

def test_crisis_section_always_included():
    prompt = _base_prompt()
    assert "КРИЗИС" in prompt or "кризис" in prompt.lower()


def test_crisis_section_present_with_scenario():
    prompt = _full_prompt("sadness_grief")
    assert "КРИЗИС" in prompt or "кризис" in prompt.lower()


def test_crisis_section_present_with_technique():
    intake = _make_intake("anxiety", risk_tier=1)
    scenario = get_scenario("anxiety")
    technique = get_technique("physiological_sigh")
    prompt = build_support_prompt(intake, scenario, technique)
    assert "КРИЗИС" in prompt or "кризис" in prompt.lower()


# ── Technique injection ───────────────────────────────────────────────────────

def test_technique_title_injected_into_prompt():
    intake = _make_intake("sadness_grief", risk_tier=1)
    scenario = get_scenario("sadness_grief")
    technique = get_technique("labeling_dbt")
    prompt = build_support_prompt(intake, scenario, technique)
    assert technique.title in prompt or "DBT" in prompt


def test_scenario_rules_injected_into_prompt():
    intake = _make_intake("sadness_grief", risk_tier=1)
    scenario = get_scenario("sadness_grief")
    prompt = build_support_prompt(intake, scenario, technique=None)
    assert "ДЕЛАЙ" in prompt or "do_rules" in prompt.lower()
    assert "НЕ ДЕЛАЙ" in prompt or "dont_rules" in prompt.lower()


def test_no_technique_when_none_provided():
    intake = _make_intake("diagnosis_request", risk_tier=1)
    scenario = get_scenario("diagnosis_request")
    prompt = build_support_prompt(intake, scenario, technique=None)
    assert "РЕКОМЕНДУЕМАЯ ТЕХНИКА" not in prompt


# ── Safety redirect scenarios produce safe prompts ────────────────────────────

def test_passive_death_thoughts_scenario_has_no_technique_prompt():
    intake = _make_intake("passive_death_thoughts", risk_tier=2)
    scenario = get_scenario("passive_death_thoughts")
    # scenario has no recommended_techniques → technique is None
    prompt = build_support_prompt(intake, scenario, technique=None)
    assert "КРИЗИС" in prompt


def test_prompt_always_specifies_reply_language():
    prompt = _base_prompt()
    assert "язык" in prompt.lower() or "language" in prompt.lower() or "на том языке" in prompt.lower()
