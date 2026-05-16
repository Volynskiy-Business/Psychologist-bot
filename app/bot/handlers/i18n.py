"""Internationalization support."""

import json
from pathlib import Path
from typing import Any

from app.config import settings

I18N_DIR = Path(__file__).parent.parent.parent.parent / "i18n"

# Cache for loaded translations
_translations: dict[str, dict[str, Any]] = {}


def load_translation(lang: str) -> dict[str, Any]:
    """Load translation file for given language."""
    if lang in _translations:
        return _translations[lang]

    file_path = I18N_DIR / f"{lang}.json"
    if not file_path.exists():
        # Fallback to English
        file_path = I18N_DIR / "en.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _translations[lang] = data
    return data


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text by dot-separated key."""
    translation = load_translation(lang)

    # Navigate nested keys
    keys = key.split(".")
    value = translation
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # Fallback to English
            en_translation = load_translation("en")
            value = en_translation
            for k2 in keys:
                if isinstance(value, dict) and k2 in value:
                    value = value[k2]
                else:
                    return key  # Return key itself if not found

    if isinstance(value, str):
        return value.format(bot_name=settings.bot_display_name, **kwargs)
    return str(value)


def get_user_language(user) -> str:
    """Get user language from Telegram user object."""
    if user and user.language_code:
        # Map Telegram language codes to our translations
        lang_map = {
            "ru": "ru",
            "en": "en",
            "de": "de",
            "fr": "fr",
            "es": "es",
            "it": "it",
            "pt": "pt",
            "pt-br": "pt",  # Brazilian Portuguese
            "no": "no",
            "nb": "no",  # Norwegian Bokmål
            "nn": "no",  # Norwegian Nynorsk
            "da": "da",
            "uk": "ru",  # Ukrainian -> Russian fallback
            "be": "ru",  # Belarusian -> Russian fallback
            "kk": "ru",  # Kazakh -> Russian fallback
            "sv": "da",  # Swedish -> Danish fallback
        }
        return lang_map.get(user.language_code, "en")
    return "en"
