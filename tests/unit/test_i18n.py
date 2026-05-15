"""Tests for i18n language detection and locale loading.

I-1: get_user_language maps "es" to "es"
I-2: Spanish locale serves classifier_unavailable in Spanish (not English fallback)
I-3: Unsupported language code falls back to "en"
I-4: Missing language_code falls back to "en"
"""

from unittest.mock import MagicMock

import pytest

import app.bot.handlers.i18n as i18n_module
from app.bot.handlers.i18n import get_text, get_user_language


@pytest.fixture(autouse=True)
def clear_translation_cache():
    """Ensure each test starts with an empty translation cache."""
    i18n_module._translations.clear()
    yield
    i18n_module._translations.clear()


def _make_user(language_code: str | None) -> MagicMock:
    user = MagicMock()
    user.language_code = language_code
    return user


def test_get_user_language_spanish() -> None:
    """I-1: Telegram language_code 'es' maps to 'es' locale."""
    assert get_user_language(_make_user("es")) == "es"


def test_spanish_classifier_unavailable_is_spanish() -> None:
    """I-2: classifier_unavailable key in 'es' locale is not the English text."""
    es_text = get_text("chat.classifier_unavailable", "es")
    en_text = get_text("chat.classifier_unavailable", "en")

    assert es_text != en_text, "Spanish text must differ from English"
    assert es_text != "chat.classifier_unavailable", "Key must exist in es.json"
    assert "Temporalmente" in es_text, "Spanish text should start with expected word"


def test_get_user_language_unsupported_falls_back_to_en() -> None:
    """I-3: Unknown Telegram language code falls back to 'en'."""
    assert get_user_language(_make_user("zh")) == "en"
    assert get_user_language(_make_user("ja")) == "en"


def test_get_user_language_none_code_falls_back_to_en() -> None:
    """I-4: Missing language_code falls back to 'en'."""
    assert get_user_language(_make_user(None)) == "en"
    assert get_user_language(None) == "en"
