"""Voice transcription: download OGG, convert to WAV, transcribe with provider fallback."""
import asyncio
import logging
import tempfile
from pathlib import Path

from aiogram import Bot
from aiogram.types import Voice

from app.services.stt.base import STTProviderError
from app.services.stt.service import STTService

logger = logging.getLogger(__name__)


async def _download_ogg(voice: Voice, bot: Bot) -> Path:
    fd, path_str = tempfile.mkstemp(suffix=".ogg")
    ogg_path = Path(path_str)
    import os
    os.close(fd)
    with open(ogg_path, "wb") as f:
        await bot.download(voice, destination=f)
    logger.info("stage=voice_download status=success")
    return ogg_path


async def _convert_to_wav(ogg_path: Path) -> Path:
    fd, path_str = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(fd)
    wav_path = Path(path_str)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(ogg_path),
        "-ar", "16000", "-ac", "1", "-f", "wav",
        str(wav_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (rc={proc.returncode}): {stderr.decode()[:200]}"
        )
    logger.info("stage=voice_convert status=success")
    return wav_path


def _cleanup(*paths: Path | None) -> None:
    failed = False
    for p in paths:
        if p is None:
            continue
        try:
            p.unlink(missing_ok=True)
        except Exception:
            logger.warning("stage=voice_temp_cleanup status=failed suffix=%s", p.suffix)
            failed = True
    if not failed:
        logger.info("stage=voice_temp_cleanup status=success")


async def transcribe_voice(voice: Voice, bot: Bot) -> str | None:
    """Download and transcribe a Telegram voice message with STT provider fallback.

    Returns the transcript string, or None on any failure.
    Pre-provider failures (download / ffmpeg) return None immediately without
    attempting STT. Provider failures return None after both providers are tried.
    """
    ogg_path: Path | None = None
    wav_path: Path | None = None
    try:
        try:
            ogg_path = await _download_ogg(voice, bot)
        except Exception:
            logger.exception("stage=voice_download status=failed")
            return None

        try:
            wav_path = await _convert_to_wav(ogg_path)
        except Exception:
            logger.exception("stage=voice_convert status=failed")
            return None

        service = STTService()
        result = await service.transcribe(wav_path)
        return result.text if result.text.strip() else None

    except STTProviderError:
        logger.error("stage=voice_transcription status=all_providers_failed")
        return None
    except Exception:
        logger.exception("stage=voice_transcription status=unexpected_error")
        return None
    finally:
        _cleanup(ogg_path, wav_path)
