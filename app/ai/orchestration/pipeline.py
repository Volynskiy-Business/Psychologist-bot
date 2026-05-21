"""Multi-agent support pipeline.

Orchestrates intake classification → scenario/technique selection →
LLM response generation → quality check → humanization rewrite (if needed) →
safety validation for each user message.
"""

import logging
from typing import Optional

from app.ai.openrouter_client import OpenRouterClient
from app.ai.orchestration.models import PipelineResult
from app.ai.output_validation import validate_support_response
from app.ai.prompts.humanization_prompt import build_humanization_prompt
from app.ai.prompts.support_agent_prompt import build_support_prompt
from app.ai.response_quality import check_response_quality
from app.ai.routing.intake import classify_intake
from app.ai.scenarios.loader import get_scenario
from app.ai.techniques.loader import select_technique

logger = logging.getLogger(__name__)


class SupportPipeline:
    def __init__(self, client: OpenRouterClient, model: Optional[str] = None) -> None:
        self.client = client
        self.model = model or None

    async def run(
        self,
        user_text: str,
        lang: str,
        history: list[dict[str, str]],
        user_profile: Optional[dict] = None,
    ) -> PipelineResult:
        # Step 1: Deterministic intake classification
        intake = classify_intake(user_text, lang)
        logger.debug(
            "stage=intake lang=%s scenario=%s emotion=%s risk_tier=%d intensity=%.2f",
            intake.language,
            intake.scenario_id,
            intake.detected_emotion,
            intake.risk_tier,
            intake.intensity,
        )

        # Step 2: Scenario and technique selection
        scenario = get_scenario(intake.scenario_id)
        technique = select_technique(scenario, intake.risk_tier.value)
        logger.debug(
            "stage=selection scenario=%s technique=%s",
            scenario.id if scenario else "none",
            technique.id if technique else "none",
        )

        # Step 3: Build context-injected system prompt
        system_prompt = build_support_prompt(intake, scenario, technique, user_profile)

        # Step 4: LLM call with full conversation history
        messages: list[dict[str, str]] = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": user_text}]
        )
        response = await self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.4,
            max_tokens=700,
        )
        draft = response.content

        # Step 5: Deterministic quality check → humanization rewrite if needed
        quality = check_response_quality(draft, intake.risk_tier)
        if quality.should_rewrite:
            logger.info(
                "stage=quality_rewrite issues=%s scenario=%s",
                quality.issues(),
                intake.scenario_id,
            )
            try:
                humanization_prompt = build_humanization_prompt(
                    draft, user_text, intake.language
                )
                rewrite_response = await self.client.chat_completion(
                    messages=[{"role": "user", "content": humanization_prompt}],
                    model=self.model,
                    temperature=0.3,
                    max_tokens=500,
                )
                draft = rewrite_response.content
            except Exception:
                logger.exception("stage=quality_rewrite failed; using original draft")

        # Step 6: Deterministic safety validation (runs after any rewrite)
        is_safe, block_reason = validate_support_response(draft)
        if not is_safe:
            logger.warning(
                "stage=output_validation blocked reason=%s scenario=%s",
                block_reason,
                intake.scenario_id,
            )

        return PipelineResult(
            content=draft,
            is_safe=is_safe,
            block_reason=block_reason,
            scenario_id=intake.scenario_id,
            technique_id=technique.id if technique else None,
            risk_tier=intake.risk_tier,
            intake_language=intake.language,
        )
