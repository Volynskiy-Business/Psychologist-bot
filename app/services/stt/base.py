from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class STTResult:
    text: str
    provider: str
    model: str


class STTProviderError(Exception):
    pass


class STTRateLimitError(STTProviderError):
    pass


class STTTemporaryError(STTProviderError):
    pass


class STTUnauthorizedError(STTProviderError):
    pass


class STTProvider(Protocol):
    provider_name: str

    async def transcribe(self, audio_path: Path) -> STTResult:
        ...
