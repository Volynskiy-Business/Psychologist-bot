"""Tests for i18n language detection and locale loading.

I-1: get_user_language maps "es" to "es"
I-2: Spanish locale serves classifier_unavailable in Spanish (not English fallback)
I-3: Unsupported language code falls back to "en"
I-4: Missing language_code falls back to "en"
I-5: All supported locales contain required keys (completeness guard)
I-6: Spanish language code displays as Español in _LANG_DISPLAY
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


_REQUIRED_KEYS = [
    "chat.classifier_unavailable",
    "mood.add_note_prompt",
    "mood.note_saved",
    "mood.buttons.add_note",
]
_SUPPORTED_LOCALES = ["en", "ru", "fr", "de", "no", "da", "pt", "es"]


@pytest.mark.parametrize("locale", _SUPPORTED_LOCALES)
@pytest.mark.parametrize("key", _REQUIRED_KEYS)
def test_locale_contains_required_key(locale: str, key: str) -> None:
    """I-5: Every supported locale must contain each required key without fallback."""
    text = get_text(key, locale)
    en_text = get_text(key, "en")
    assert text != key, f"Key '{key}' missing from locale '{locale}'"
    assert text != en_text or locale == "en", (
        f"Key '{key}' in locale '{locale}' falls back to English — add a translation"
    )


def test_spanish_displays_as_espanol() -> None:
    """I-6: _LANG_DISPLAY maps 'es' to the Spanish label, not the English fallback."""
    from app.bot.handlers.start import _LANG_DISPLAY

    assert "es" in _LANG_DISPLAY, "'es' must be present in _LANG_DISPLAY"
    assert "Español" in _LANG_DISPLAY["es"]
    assert _LANG_DISPLAY["es"] != _LANG_DISPLAY["en"]
