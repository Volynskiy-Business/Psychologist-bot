from __future__ import annotations

import logging
from pathlib import Path

from groq import APIConnectionError, APIStatusError, AsyncGroq, RateLimitError

from app.services.stt.base import (
    STTProviderError,
    STTRateLimitError,
    STTResult,
    STTTemporaryError,
)

logger = logging.getLogger(__name__)

_MODEL = "whisper-large-v3-turbo"


class GroqSTTProvider:
    provider_name = "groq"

    async def transcribe(self, audio_path: Path) -> STTResult:
        from app.config import settings

        if not settings.groq_api_key:
            raise STTProviderError("Groq API key not configured")

        try:
            audio_bytes = audio_path.read_bytes()
            client = AsyncGroq(api_key=settings.groq_api_key.get_secret_value())
            result = await client.audio.transcriptions.create(
                file=(audio_path.name, audio_bytes, "audio/wav"),
                model=_MODEL,
            )
            return STTResult(text=result.text.strip(), provider=self.provider_name, model=_MODEL)
        except RateLimitError as exc:
            raise STTRateLimitError("Groq rate limit exceeded") from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise STTTemporaryError(f"Groq server error: {exc.status_code}") from exc
            raise STTProviderError(f"Groq API error: {exc.status_code}") from exc
        except APIConnectionError as exc:
            raise STTTemporaryError("Groq connection error") from exc
        except (STTRateLimitError, STTTemporaryError, STTProviderError):
            raise
        except Exception as exc:
            raise STTProviderError(f"Groq unexpected error: {exc}") from exc
