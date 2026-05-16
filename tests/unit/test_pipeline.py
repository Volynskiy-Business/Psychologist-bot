"""Tests for the SupportPipeline — mocks the LLM client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.orchestration.models import RiskTier
from app.ai.orchestration.pipeline import SupportPipeline


def _make_client(content: str = "Я слышу тебя. Это нормальная реакция.") -> MagicMock:
    fake_response = MagicMock()
    fake_response.content = content
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value=fake_response)
    return client


@pytest.mark.asyncio
async def test_pipeline_returns_result_for_normal_message():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("мне грустно", lang="ru", history=[])
    assert result.content == "Я слышу тебя. Это нормальная реакция."
    assert result.is_safe is True
    assert result.block_reason is None


@pytest.mark.asyncio
async def test_pipeline_selects_scenario_for_sadness():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("мне грустно и тоскливо", lang="ru", history=[])
    assert result.scenario_id == "sadness_grief"


@pytest.mark.asyncio
async def test_pipeline_selects_technique_for_matched_scenario():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("я тревожусь и беспокоюсь", lang="ru", history=[])
    assert result.scenario_id == "anxiety"
    assert result.technique_id is not None


@pytest.mark.asyncio
async def test_pipeline_no_technique_for_diagnosis_request():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run(
        "поставьте мне диагноз, у меня депрессия?", lang="ru", history=[]
    )
    assert result.scenario_id == "diagnosis_request"
    assert result.technique_id is None


@pytest.mark.asyncio
async def test_pipeline_system_prompt_is_first_message():
    client = _make_client()
    pipeline = SupportPipeline(client)
    await pipeline.run("мне грустно", lang="ru", history=[])
    call_args = client.chat_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    assert messages[0]["role"] == "system"
    assert len(messages[0]["content"]) > 100


@pytest.mark.asyncio
async def test_pipeline_injects_history_after_system_prompt():
    client = _make_client()
    pipeline = SupportPipeline(client)
    history = [
        {"role": "user", "content": "Предыдущее сообщение"},
        {"role": "assistant", "content": "Предыдущий ответ"},
    ]
    await pipeline.run("мне грустно", lang="ru", history=history)
    call_args = client.chat_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "Предыдущее сообщение"
    assert messages[2]["content"] == "Предыдущий ответ"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "мне грустно"


@pytest.mark.asyncio
async def test_pipeline_marks_blocked_content_unsafe():
    client = _make_client("I am your doctor and you have depression disorder.")
    pipeline = SupportPipeline(client)
    result = await pipeline.run("мне грустно", lang="ru", history=[])
    assert result.is_safe is False
    assert result.block_reason is not None


@pytest.mark.asyncio
async def test_pipeline_propagates_llm_exception():
    client = MagicMock()
    client.chat_completion = AsyncMock(side_effect=RuntimeError("API timeout"))
    pipeline = SupportPipeline(client)
    with pytest.raises(RuntimeError, match="API timeout"):
        await pipeline.run("мне грустно", lang="ru", history=[])


@pytest.mark.asyncio
async def test_pipeline_risk_tier_in_result():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("мне грустно", lang="ru", history=[])
    assert isinstance(result.risk_tier, RiskTier)


@pytest.mark.asyncio
async def test_pipeline_intake_language_in_result():
    client = _make_client()
    pipeline = SupportPipeline(client)
    result = await pipeline.run("I feel anxious", lang="en", history=[])
    assert result.intake_language == "en"


@pytest.mark.asyncio
async def test_pipeline_scenario_prompt_contains_technique():
    """System prompt must mention the technique when one is selected."""
    client = _make_client()
    pipeline = SupportPipeline(client)
    await pipeline.run("мне грустно", lang="ru", history=[])
    call_args = client.chat_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    system_content = messages[0]["content"]
    # Sadness scenario selects labeling_dbt — its title should appear in system prompt
    assert "DBT" in system_content or "Называние" in system_content


@pytest.mark.asyncio
async def test_pipeline_safety_boundary_no_diagnosis_claim():
    """Support agent prompt must not produce an uncaught diagnosis claim."""
    # Simulate LLM producing a diagnosis — pipeline should block it
    client = _make_client("You are diagnosed with anxiety disorder.")
    pipeline = SupportPipeline(client)
    result = await pipeline.run("расскажи что со мной", lang="ru", history=[])
    assert result.is_safe is False
