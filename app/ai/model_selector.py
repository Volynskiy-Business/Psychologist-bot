"""Smart model selector with ranking and fallback."""

import time
from dataclasses import dataclass
from typing import Optional

from app.ai.openrouter_client import OpenRouterClient, OpenRouterModel
from app.config import settings


@dataclass
class ModelScore:
    model: OpenRouterModel
    score: float
    reasons: list[str]


class ModelSelector:
    """Selects the best free model based on quality metrics."""

    # Preferred models in order of quality for Russian language
    PREFERRED_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-super-120b-a4b:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "openai/gpt-oss-120b:free",
    ]

    def __init__(self, client: OpenRouterClient) -> None:
        self.client = client
        self._cache: Optional[list[OpenRouterModel]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 300  # 5 minutes

    async def get_available_models(self) -> list[OpenRouterModel]:
        """Get cached list of available models."""
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        models = await self.client.list_models()
        # Filter free models
        free_models = [
            m for m in models if m.pricing_prompt == "0" and m.pricing_completion == "0"
        ]
        self._cache = free_models
        self._cache_time = now
        return free_models

    def _score_model(self, model: OpenRouterModel) -> ModelScore:
        """Score a model based on quality metrics."""
        score = 0.0
        reasons = []

        # Prefer larger context
        if model.context_length >= 128000:
            score += 30
            reasons.append("Large context (128k+)")
        elif model.context_length >= 64000:
            score += 20
            reasons.append("Medium context (64k+)")
        elif model.context_length >= 32000:
            score += 10
            reasons.append("Small context (32k+)")

        # Prefer known good models
        if model.id in self.PREFERRED_MODELS:
            rank = self.PREFERRED_MODELS.index(model.id)
            score += (len(self.PREFERRED_MODELS) - rank) * 10
            reasons.append(f"Preferred model (rank {rank + 1})")

        # Prefer models with good reputation
        if "llama" in model.id.lower():
            score += 15
            reasons.append("Llama family")
        elif "gemma" in model.id.lower():
            score += 10
            reasons.append("Gemma family")
        elif "qwen" in model.id.lower():
            score += 10
            reasons.append("Qwen family")

        return ModelScore(model=model, score=score, reasons=reasons)

    async def select_model(self) -> str:
        """Select the best available model."""
        try:
            models = await self.get_available_models()
            if not models:
                return settings.default_model  # Fallback to openrouter/free

            # Score all models
            scored = [self._score_model(m) for m in models]
            scored.sort(key=lambda x: x.score, reverse=True)

            # Log selection
            top = scored[0]
            print(
                f"Selected model: {top.model.id} (score: {top.score}, reasons: {top.reasons})"
            )

            return top.model.id
        except Exception:
            return settings.default_model

    async def get_fallback_chain(self) -> list[str]:
        """Get ordered list of fallback models."""
        models = await self.get_available_models()
        model_ids = {m.id for m in models}

        # Build fallback chain
        fallbacks = []
        for preferred in self.PREFERRED_MODELS:
            if preferred in model_ids:
                fallbacks.append(preferred)

        # Always add openrouter/free as last resort
        if settings.default_model not in fallbacks:
            fallbacks.append(settings.default_model)

        return fallbacks
