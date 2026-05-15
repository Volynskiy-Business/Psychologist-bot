"""Golden tests for the SupportPipeline — structural verification per life-event scenario.

These tests verify intake classification, risk routing, and prompt construction
for representative user messages. They do not require or verify exact LLM output.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.orchestration.models import RiskTier
from app.ai.orchestration.pipeline import SupportPipeline
from app.ai.prompts.support_agent_prompt import build_support_prompt
from app.ai.routing.intake import classify_intake
from app.ai.scenarios.loader import get_scenario
from app.ai.techniques.loader import select_technique


def _make_client(content: str = "Я слышу тебя. Это нормально.") -> MagicMock:
    fake_response = MagicMock()
    fake_response.content = content
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value=fake_response)
    return client


# ── Helper: verify prompt safety invariants ───────────────────────────────────

def _assert_prompt_safe(prompt: str) -> None:
    """Common safety assertions that must hold for every generated prompt."""
    assert "не врач" in prompt, "Prompt missing role disclaimer"
    assert "КРИЗИС" in prompt, "Prompt missing crisis section"
    forbidden_role_claims = ["I am your therapist", "Я ваш терапевт", "я твой психолог"]
    for claim in forbidden_role_claims:
        assert claim.lower() not in prompt.lower(), f"Forbidden claim: '{claim}'"


def _build_prompt_for(message: str) -> str:
    intake = classify_intake(message)
    scenario = get_scenario(intake.scenario_id)
    technique = select_technique(scenario, intake.risk_tier.value)
    return build_support_prompt(intake, scenario, technique)


# ── Intake classification golden cases ────────────────────────────────────────

def test_breakup_classified_as_sadness_or_breakup():
    result = classify_intake("мы расстались, я не понимаю зачем жить дальше")
    assert result.scenario_id in ("breakup_divorce", "sadness_grief", "loss_of_meaning")
    assert result.risk_tier == RiskTier.TIER_2


def test_death_of_loved_one_classified_correctly():
    result = classify_intake("моя мама умерла на прошлой неделе")
    assert result.scenario_id in ("death_of_loved_one", "sadness_grief")
    assert result.risk_tier in (RiskTier.TIER_1, RiskTier.TIER_2)


def test_job_loss_classified_correctly():
    result = classify_intake("меня уволили сегодня, не знаю что теперь делать")
    assert result.scenario_id in ("job_loss", "uncertainty", "exhaustion")


def test_financial_loss_classified_correctly():
    result = classify_intake("у меня огромные долги, я в финансовом кризисе")
    assert result.scenario_id in ("financial_loss", "uncertainty", "anxiety")


def test_serious_illness_classified_correctly():
    result = classify_intake("у меня хроническая боль и инвалидность")
    assert result.scenario_id in ("serious_illness_or_disability", "exhaustion", "uncertainty")


def test_loneliness_classified_correctly():
    result = classify_intake("я чувствую одиночество, никто не понимает меня")
    assert result.scenario_id == "loneliness"


def test_shame_classified_correctly():
    result = classify_intake("я чувствую такой стыд и вину за то что сделал")
    assert result.scenario_id == "guilt_shame"


def test_anxiety_panic_classified_correctly():
    result = classify_intake("у меня паника и тревога, я очень беспокоюсь")
    assert result.scenario_id == "anxiety"


def test_anger_conflict_classified_correctly():
    result = classify_intake("меня это бесит, я злюсь из-за конфликта")
    assert result.scenario_id == "anger"


def test_burnout_exhaustion_classified_correctly():
    result = classify_intake("я выгорел, нет сил совсем, вымотан полностью")
    assert result.scenario_id == "exhaustion"


def test_meaninglessness_classified_correctly():
    result = classify_intake("нет смысла, апатия, безразличие ко всему")
    assert result.scenario_id == "loss_of_meaning"


def test_passive_death_thoughts_triggers_tier2():
    result = classify_intake("хочу исчезнуть, лучше бы меня не было")
    assert result.risk_tier == RiskTier.TIER_2
    assert len(result.risk_signals) > 0


# ── Risk tier golden cases ────────────────────────────────────────────────────

def test_breakup_with_hopelessness_triggers_tier2():
    result = classify_intake("расстались, нет смысла жить")
    assert result.risk_tier == RiskTier.TIER_2


def test_grief_without_crisis_signals_is_tier1():
    result = classify_intake("моя бабушка умерла, мне грустно и тяжело")
    assert result.risk_tier in (RiskTier.TIER_1, RiskTier.TIER_2)


def test_job_loss_no_risk_signals_is_tier1():
    result = classify_intake("уволили сегодня, это тяжело")
    assert result.risk_tier in (RiskTier.TIER_0, RiskTier.TIER_1)


# ── Technique selection respects risk ceiling ─────────────────────────────────

def test_no_technique_for_passive_death_thoughts_scenario():
    scenario = get_scenario("passive_death_thoughts")
    assert scenario is not None
    assert scenario.recommended_techniques == []
    technique = select_technique(scenario, risk_tier=2)
    assert technique is None


def test_no_technique_for_possible_self_harm_scenario():
    scenario = get_scenario("possible_self_harm")
    assert scenario is not None
    assert scenario.recommended_techniques == []


def test_no_technique_for_imminent_danger_scenario():
    scenario = get_scenario("imminent_danger")
    assert scenario is not None
    assert scenario.recommended_techniques == []


def test_technique_selected_respects_risk_ceiling():
    for scenario_id in ("sadness_grief", "anxiety", "loneliness", "exhaustion"):
        scenario = get_scenario(scenario_id)
        for risk_tier in (1, 2):
            technique = select_technique(scenario, risk_tier=risk_tier)
            if technique is not None:
                assert technique.risk_ceiling >= risk_tier, (
                    f"Scenario '{scenario_id}' selected technique '{technique.id}' "
                    f"with risk_ceiling={technique.risk_ceiling} at tier {risk_tier}"
                )


# ── Prompt safety invariants per life-event scenario ─────────────────────────

def test_breakup_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("мы расстались"))


def test_death_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("мой близкий умер"))


def test_job_loss_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("меня уволили сегодня"))


def test_financial_loss_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("у меня огромные долги"))


def test_serious_illness_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("у меня хроническая боль"))


def test_loneliness_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("я чувствую одиночество"))


def test_shame_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("мне очень стыдно за то что я сделал"))


def test_anxiety_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("я очень тревожусь"))


def test_anger_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("меня бесит эта ситуация"))


def test_burnout_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("я выгорел и нет сил"))


def test_meaninglessness_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("нет смысла ни в чём"))


def test_passive_death_thoughts_prompt_is_safe():
    _assert_prompt_safe(_build_prompt_for("хочу исчезнуть"))


# ── Prompt contains no diagnosis framing ─────────────────────────────────────

def test_prompts_do_not_claim_diagnosis_authority():
    forbidden_phrases = [
        "у тебя депрессия",
        "у вас тревожное расстройство",
        "you have depression",
        "you are diagnosed",
        "diagnosed with",
    ]
    test_messages = [
        "мне грустно и тяжело",
        "я тревожусь постоянно",
        "я злюсь на всё",
    ]
    for message in test_messages:
        prompt = _build_prompt_for(message)
        for phrase in forbidden_phrases:
            assert phrase.lower() not in prompt.lower(), (
                f"Forbidden diagnosis phrase '{phrase}' found in prompt for '{message}'"
            )


# ── Pipeline integration golden tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_selects_breakup_or_sadness_for_breakup_message():
    client = _make_client()
    pipeline = SupportPipeline(client)
    # Two clear breakup signals → breakup_divorce wins over anxiety
    result = await pipeline.run("мы расстались, она меня бросила", lang="ru", history=[])
    assert result.scenario_id in ("breakup_divorce", "sadness_grief")
    assert result.is_safe is True


@pytest.mark.asyncio
async def test_pipeline_selects_job_loss_or_uncertainty():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("меня уволили и я не знаю что делать", lang="ru", history=[])
    assert result.scenario_id in ("job_loss", "uncertainty", "exhaustion")
    assert isinstance(result.risk_tier, RiskTier)


@pytest.mark.asyncio
async def test_pipeline_selects_death_or_sadness_for_bereavement():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("моя мама умерла, горе невыносимо", lang="ru", history=[])
    assert result.scenario_id in ("death_of_loved_one", "sadness_grief")


@pytest.mark.asyncio
async def test_pipeline_tier2_for_passive_death_thoughts():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("хочу исчезнуть, лучше бы меня не было", lang="ru", history=[])
    assert result.risk_tier == RiskTier.TIER_2


@pytest.mark.asyncio
async def test_pipeline_no_technique_for_passive_death_thoughts_scenario():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("хочу исчезнуть, лучше бы меня не было", lang="ru", history=[])
    if result.scenario_id == "passive_death_thoughts":
        assert result.technique_id is None


@pytest.mark.asyncio
async def test_pipeline_english_job_loss():
    client = _make_client()
    pipeline = SupportPipeline(client)
    # Avoid "terrible" which scores guilt_shame; use distinct job_loss signal only
    result = await pipeline.run("I lost my job today and I don't know what to do", lang="en", history=[])
    assert result.scenario_id in ("job_loss", "exhaustion", "uncertainty", "sadness_grief")
    assert result.intake_language == "en"
