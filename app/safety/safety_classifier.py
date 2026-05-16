"""LLM-based safety classification."""

import json
import logging
from typing import Any, Optional

import httpx

from app.ai.openrouter_client import OpenRouterClient
from app.ai.prompts.safety_classifier_prompt import SAFETY_CLASSIFIER_PROMPT
from app.db.models import RiskLevel

logger = logging.getLogger(__name__)


class SafetyClassification:
    def __init__(self, data: dict[str, Any]) -> None:
        self.risk_level = RiskLevel(data.get("risk_level", 0))
        self.risk_type = data.get("risk_type", "none")
        self.confidence = data.get("confidence", 0.0)
        self.reason = data.get("reason", "")
        self.requires_crisis_response = data.get("requires_crisis_response", False)
        self.requires_professional_referral = data.get(
            "requires_professional_referral", False
        )


class SafetyClassifier:
    def __init__(
        self,
        client: OpenRouterClient,
        model: Optional[str] = None,
        fallback_models: Optional[list[str]] = None,
    ) -> None:
        self.client = client
        self.model = model or None
        self.fallback_models = fallback_models or []

    async def classify(
        self, user_message: str, context: str = ""
    ) -> SafetyClassification:
        messages = [
            {"role": "system", "content": SAFETY_CLASSIFIER_PROMPT},
            {
                "role": "user",
                "content": f"Контекст: {context}\n\nСообщение пользователя: {user_message}",
            },
        ]

        models_to_try = [self.model] + [
            m for m in self.fallback_models if m != self.model
        ]
        last_exc: Optional[Exception] = None

        for model in models_to_try:
            try:
                response = await self.client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=0.0,
                    max_tokens=200,
                    response_format={"type": "json_object"},
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429:
                    logger.warning(
                        "stage=classifier error=rate_limited model=%s; trying next",
                        model or "default",
                    )
                    last_exc = exc
                    continue
                if status in (401, 403):
                    logger.error(
                        "stage=classifier error=auth_config model=%s status=%d",
                        model or "default",
                        status,
                    )
                else:
                    logger.error(
                        "stage=classifier error=http model=%s status=%d",
                        model or "default",
                        status,
                    )
                raise
            except httpx.TimeoutException:
                logger.warning(
                    "stage=classifier error=timeout model=%s", model or "default"
                )
                raise
            except httpx.ConnectError:
                logger.warning(
                    "stage=classifier error=network model=%s", model or "default"
                )
                raise

            try:
                data = json.loads(response.content)
                return SafetyClassification(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                logger.warning(
                    "stage=classifier error=parse_failed model=%s", model or "default"
                )
                return SafetyClassification(
                    {
                        "risk_level": 2,
                        "risk_type": "unknown",
                        "confidence": 0.0,
                        "reason": "Failed to parse classifier response",
                        "requires_crisis_response": False,
                        "requires_professional_referral": True,
                    }
                )

        logger.error(
            "stage=classifier error=all_models_rate_limited models=%s", models_to_try
        )
        raise last_exc  # type: ignore[misc]
