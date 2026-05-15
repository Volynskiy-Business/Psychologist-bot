"""OpenRouter API client with retries and logging."""

import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings


@dataclass
class OpenRouterResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


@dataclass
class OpenRouterModel:
    id: str
    name: str
    context_length: int
    pricing_prompt: str
    pricing_completion: str


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key.get_secret_value()
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.default_model = settings.default_model
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://t.me/",
                "X-Title": settings.bot_display_name,
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_is_retriable),
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 700,
        response_format: Optional[dict[str, Any]] = None,
    ) -> OpenRouterResponse:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        start = time.monotonic()
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        latency_ms = int((time.monotonic() - start) * 1000)

        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return OpenRouterResponse(
            content=choice["message"]["content"],
            model=data.get("model", model or self.default_model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

    async def list_models(self) -> list[OpenRouterModel]:
        response = await self.client.get(f"{self.base_url}/models")
        response.raise_for_status()
        data = response.json()

        models = []
        for m in data.get("data", []):
            pricing = m.get("pricing", {})
            models.append(
                OpenRouterModel(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    context_length=m.get("context_length", 0),
                    pricing_prompt=pricing.get("prompt", "0"),
                    pricing_completion=pricing.get("completion", "0"),
                )
            )
        return models

    async def healthcheck(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/models", timeout=10.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.aclose()
