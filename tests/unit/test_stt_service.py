"""Tests for STT service: provider fallback, cleanup, and temp file handling."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.stt.base import (
    STTProviderError,
    STTRateLimitError,
    STTResult,
    STTTemporaryError,
)


def _mock_provider(name: str, result: STTResult | None = None, side_effect=None):
    p = MagicMock()
    p.provider_name = name
    p.transcribe = AsyncMock()
    if side_effect is not None:
        p.transcribe.side_effect = side_effect
    elif result is not None:
        p.transcribe.return_value = result
    return p


def _make_service(primary, fallback=None):
    from app.services.stt.service import STTService
    svc = object.__new__(STTService)
    svc.primary = primary
    svc.fallback = fallback
    return svc


@pytest.fixture
def audio_path(tmp_path) -> Path:
    p = tmp_path / "test.wav"
    p.write_bytes(b"fake wav data")
    return p


@pytest.fixture
def groq_result() -> STTResult:
    return STTResult(text="hello world", provider="groq", model="whisper-large-v3-turbo")


@pytest.fixture
def deepgram_result() -> STTResult:
    return STTResult(text="fallback text", provider="deepgram", model="nova-3")


# ---------------------------------------------------------------------------
# Test 1: Groq success — Deepgram not called
# ---------------------------------------------------------------------------

async def test_groq_success_deepgram_not_called(audio_path, groq_result, deepgram_result):
    deepgram = _mock_provider("deepgram", result=deepgram_result)
    service = _make_service(
        primary=_mock_provider("groq", result=groq_result),
        fallback=deepgram,
    )

    result = await service.transcribe(audio_path)

    assert result.provider == "groq"
    assert result.text == "hello world"
    deepgram.transcribe.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Groq 429 → Deepgram success
# ---------------------------------------------------------------------------

async def test_groq_rate_limit_falls_back_to_deepgram(audio_path, deepgram_result):
    service = _make_service(
        primary=_mock_provider("groq", side_effect=STTRateLimitError("429")),
        fallback=_mock_provider("deepgram", result=deepgram_result),
    )

    result = await service.transcribe(audio_path)

    assert result.provider == "deepgram"
    assert result.text == "fallback text"


# ---------------------------------------------------------------------------
# Test 3: Groq timeout (STTTemporaryError) → Deepgram success
# ---------------------------------------------------------------------------

async def test_groq_temporary_error_falls_back_to_deepgram(audio_path, deepgram_result):
    service = _make_service(
        primary=_mock_provider("groq", side_effect=STTTemporaryError("timeout")),
        fallback=_mock_provider("deepgram", result=deepgram_result),
    )

    result = await service.transcribe(audio_path)

    assert result.provider == "deepgram"
    assert result.text == "fallback text"


# ---------------------------------------------------------------------------
# Test 4: Groq error → Deepgram error → STTProviderError raised
# ---------------------------------------------------------------------------

async def test_both_providers_fail_raises(audio_path):
    service = _make_service(
        primary=_mock_provider("groq", side_effect=STTRateLimitError("429")),
        fallback=_mock_provider("deepgram", side_effect=STTTemporaryError("dg fail")),
    )

    with pytest.raises(STTProviderError):
        await service.transcribe(audio_path)


# ---------------------------------------------------------------------------
# Test 5: Deepgram not configured (missing API key) → no Deepgram call
# ---------------------------------------------------------------------------

def test_deepgram_not_configured_when_key_missing():
    with patch("app.config.settings") as mock_cfg:
        mock_cfg.stt_fallback_provider = "deepgram"
        mock_cfg.deepgram_api_key = ""

        from app.services.stt.service import STTService
        svc = STTService()

    assert svc.fallback is None


async def test_groq_fail_no_fallback_raises(audio_path):
    service = _make_service(
        primary=_mock_provider("groq", side_effect=STTRateLimitError("429")),
        fallback=None,
    )

    with pytest.raises(STTProviderError):
        await service.transcribe(audio_path)


# ---------------------------------------------------------------------------
# Test 6: Empty Groq transcript → Deepgram fallback used
# ---------------------------------------------------------------------------

async def test_empty_groq_transcript_triggers_fallback(audio_path, deepgram_result):
    groq_empty = STTResult(text="", provider="groq", model="whisper-large-v3-turbo")
    service = _make_service(
        primary=_mock_provider("groq", result=groq_empty),
        fallback=_mock_provider("deepgram", result=deepgram_result),
    )

    result = await service.transcribe(audio_path)

    assert result.provider == "deepgram"
    assert result.text == "fallback text"


# ---------------------------------------------------------------------------
# Test 7: Temp files always deleted — even when both providers fail
# ---------------------------------------------------------------------------

async def test_temp_files_cleaned_up_after_both_providers_fail(tmp_path):
    ogg = tmp_path / "voice.ogg"
    wav = tmp_path / "voice.wav"
    ogg.write_bytes(b"fake ogg")
    wav.write_bytes(b"fake wav")

    with (
        patch("app.ai.voice_transcription._download_ogg", new=AsyncMock(return_value=ogg)),
        patch("app.ai.voice_transcription._convert_to_wav", new=AsyncMock(return_value=wav)),
        patch(
            "app.ai.voice_transcription.STTService.transcribe",
            new=AsyncMock(side_effect=STTProviderError("all failed")),
        ),
    ):
        from app.ai.voice_transcription import transcribe_voice
        voice_mock = MagicMock()
        bot_mock = MagicMock()

        result = await transcribe_voice(voice_mock, bot_mock)

    assert result is None
    assert not ogg.exists(), "OGG temp file was not deleted"
    assert not wav.exists(), "WAV temp file was not deleted"
