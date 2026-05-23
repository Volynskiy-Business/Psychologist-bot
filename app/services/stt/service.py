from __future__ import annotations

import logging
from pathlib import Path

from app.services.stt.base import (
    STTProviderError,
    STTRateLimitError,
    STTResult,
    STTTemporaryError,
)
from app.services.stt.deepgram_provider import DeepgramSTTProvider
from app.services.stt.groq_provider import GroqSTTProvider

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self) -> None:
        self.primary = GroqSTTProvider()
        self.fallback = self._build_fallback_provider()

    def _build_fallback_provider(self) -> DeepgramSTTProvider | None:
        from app.config import settings

        if settings.stt_fallback_provider.lower() == "deepgram":
            if not settings.deepgram_api_key:
                logger.warning(
                    "stage=stt_fallback_configured provider=deepgram status=missing_api_key"
                )
                return None
            return DeepgramSTTProvider()
        return None

    async def transcribe(self, audio_path: Path) -> STTResult:
        try:
            result = await self.primary.transcribe(audio_path)
            if result.text.strip():
                logger.info(
                    "stage=stt provider=%s model=%s status=success fallback_used=false",
                    result.provider,
                    result.model,
                )
                return result
            raise STTTemporaryError("Primary STT returned empty transcription")

        except (STTRateLimitError, STTTemporaryError, STTProviderError) as exc:
            logger.warning(
                "stage=stt provider=groq status=failed fallback_available=%s error_type=%s",
                bool(self.fallback),
                type(exc).__name__,
            )

            if self.fallback is None:
                raise

            try:
                fallback_result = await self.fallback.transcribe(audio_path)
                if fallback_result.text.strip():
                    logger.info(
                        "stage=stt provider=%s model=%s status=success fallback_used=true",
                        fallback_result.provider,
                        fallback_result.model,
                    )
                    return fallback_result
                raise STTTemporaryError("Fallback STT returned empty transcription")

            except STTProviderError as fallback_exc:
                logger.error(
                    "stage=stt provider=deepgram status=failed error_type=%s",
                    type(fallback_exc).__name__,
                )
                raise fallback_exc
