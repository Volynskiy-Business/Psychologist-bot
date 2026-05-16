"""Tests for Settings config validation — free-model guard and model parsing."""

import os
from unittest import mock

import pytest
from pydantic import ValidationError

from app.config import Settings

_MINIMAL = {
    "BOT_TOKEN": "dummy-token",
    "OPENROUTER_API_KEY": "dummy-key",
    "DATABASE_URL": "sqlite+aiosqlite:///./test.db",
    "CLASSIFIER_MODEL": "",
    "OPENROUTER_FALLBACK_MODELS": "",
    "ALLOW_FREE_MODELS": "false",
}


def _make(**overrides) -> Settings:
    env = dict(_MINIMAL)
    env.update(overrides)
    with mock.patch.dict(os.environ, env):
        return Settings(_env_file=None)


# --- production model acceptance ---


def test_production_accepts_gemini_flash_lite() -> None:
    s = _make(
        APP_ENV="production",
        OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
        OPENROUTER_FALLBACK_MODELS="google/gemini-2.5-flash",
    )
    assert s.default_model == "google/gemini-2.5-flash-lite"
    assert s.fallback_models == ["google/gemini-2.5-flash"]


def test_production_rejects_free_default_model() -> None:
    with pytest.raises(ValidationError, match=":free"):
        _make(
            APP_ENV="production",
            OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
        )


def test_production_rejects_free_model_in_fallback() -> None:
    with pytest.raises(ValidationError, match=":free"):
        _make(
            APP_ENV="production",
            OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
            OPENROUTER_FALLBACK_MODELS="google/gemini-2.5-flash:free",
        )


def test_production_rejects_free_model_even_when_allow_flag_set() -> None:
    with pytest.raises(ValidationError, match=":free"):
        _make(
            APP_ENV="production",
            OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
            ALLOW_FREE_MODELS="true",
        )


# --- development model gates ---


def test_development_allows_free_with_flag() -> None:
    s = _make(
        APP_ENV="development",
        OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
        ALLOW_FREE_MODELS="true",
    )
    assert s.default_model == "meta-llama/llama-3.3-70b-instruct:free"


def test_development_rejects_free_without_flag() -> None:
    with pytest.raises(ValidationError, match=":free"):
        _make(
            APP_ENV="development",
            OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
            ALLOW_FREE_MODELS="false",
        )


# --- classifier model handling ---


def test_empty_classifier_model_is_valid() -> None:
    s = _make(
        APP_ENV="production",
        OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
        CLASSIFIER_MODEL="",
    )
    assert s.classifier_model == ""


def test_non_free_classifier_model_is_valid() -> None:
    s = _make(
        APP_ENV="production",
        OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
        CLASSIFIER_MODEL="google/gemini-2.5-flash",
    )
    assert s.classifier_model == "google/gemini-2.5-flash"


def test_production_rejects_free_classifier_model() -> None:
    with pytest.raises(ValidationError, match=":free"):
        _make(
            APP_ENV="production",
            OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
            CLASSIFIER_MODEL="meta-llama/llama-3.3-70b-instruct:free",
        )


# --- fallback model parsing ---


def test_fallback_models_parse_comma_separated() -> None:
    s = _make(
        APP_ENV="production",
        OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
        OPENROUTER_FALLBACK_MODELS="google/gemini-2.5-flash,google/gemini-2.0-flash-lite",
    )
    assert s.fallback_models == ["google/gemini-2.5-flash", "google/gemini-2.0-flash-lite"]


def test_empty_fallback_models_returns_empty_list() -> None:
    s = _make(
        APP_ENV="production",
        OPENROUTER_MODEL="google/gemini-2.5-flash-lite",
        OPENROUTER_FALLBACK_MODELS="",
    )
    assert s.fallback_models == []
