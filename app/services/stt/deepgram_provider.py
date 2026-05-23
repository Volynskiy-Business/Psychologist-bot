from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.services.stt.base import (
    STTProviderError,
    STTRateLimitError,
    STTResult,
    STTTemporaryError,
    STTUnauthorizedError,
)

logger = logging.getLogger(__name__)

_DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


class DeepgramSTTProvider:
    provider_name = "deepgram"

    async def transcribe(self, audio_path: Path) -> STTResult:
        from app.config import settings

        model = settings.stt_deepgram_model
        try:
            audio_bytes = audio_path.read_bytes()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _DEEPGRAM_URL,
                    params={"model": model},
                    content=audio_bytes,
                    headers={
                        "Authorization": f"Token {settings.deepgram_api_key}",
                        "Content-Type": "audio/wav",
                    },
                )

            if response.status_code in (401, 403):
                raise STTUnauthorizedError(f"Deepgram auth error: {response.status_code}")
            if response.status_code == 429:
                raise STTRateLimitError("Deepgram rate limit exceeded")
            if response.status_code >= 500:
                raise STTTemporaryError(f"Deepgram server error: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
            return STTResult(
                text=transcript.strip(),
                provider=self.provider_name,
                model=model,
            )

        except (STTUnauthorizedError, STTRateLimitError, STTTemporaryError, STTProviderError):
            raise
        except (KeyError, IndexError) as exc:
            raise STTProviderError("Deepgram malformed response") from exc
        except httpx.TimeoutException as exc:
            raise STTTemporaryError("Deepgram timeout") from exc
        except httpx.NetworkError as exc:
            raise STTTemporaryError("Deepgram network error") from exc
        except httpx.HTTPStatusError as exc:
            raise STTProviderError(
                f"Deepgram HTTP error: {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            raise STTProviderError(f"Deepgram unexpected error: {exc}") from exc
