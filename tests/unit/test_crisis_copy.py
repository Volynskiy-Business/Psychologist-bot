"""Tests for crisis response copy quality: no Russia-specific content, no Markdown lists."""

import re

import pytest

from app.bot.handlers.i18n import get_text


_RUSSIA_SPECIFIC_PATTERNS = [
    "8-800",
    "8 800",
    "8 (800)",
    "телефон доверия",
    "телефона доверия",
]

_MARKDOWN_LIST_PATTERNS = [
    (r"^\s*\d+\.", "numbered list marker"),
    (r"^\s*[-*•]", "bullet list marker"),
]


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_crisis_response_no_russia_specific_content(lang: str) -> None:
    """crisis.response must not contain Russia-specific crisis numbers or services."""
    text = get_text("crisis.response", lang)
    for pattern in _RUSSIA_SPECIFIC_PATTERNS:
        assert pattern not in text, (
            f"Russia-specific content '{pattern}' found in crisis.response ({lang})"
        )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_crisis_response_no_markdown_list_formatting(lang: str) -> None:
    """crisis.response must not use numbered lists or bullet points."""
    text = get_text("crisis.response", lang)
    for regex, label in _MARKDOWN_LIST_PATTERNS:
        assert not re.search(regex, text, re.MULTILINE), (
            f"Markdown {label} found in crisis.response ({lang})"
        )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_crisis_response_no_anti_dependency_phrases(lang: str) -> None:
    """crisis.response must not position the bot as the main safety resource."""
    text = get_text("crisis.response", lang)
    dependency_phrases = [
        "stay with you in chat",
        "I can stay with you",
        "быть рядом в переписке",
        "могу быть рядом в переписке",
    ]
    for phrase in dependency_phrases:
        assert phrase not in text, (
            f"Anti-dependency phrase '{phrase}' found in crisis.response ({lang})"
        )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_crisis_response_is_nonempty_and_safety_first(lang: str) -> None:
    """crisis.response must be non-empty and reference emergency/local services."""
    text = get_text("crisis.response", lang)
    assert len(text) > 50, f"crisis.response ({lang}) is too short to be meaningful"
    safety_terms_en = ["emergency", "crisis line", "local"]
    safety_terms_ru = ["экстренн", "кризисн", "местн"]
    terms = safety_terms_en if lang == "en" else safety_terms_ru
    assert any(term in text.lower() for term in terms), (
        f"crisis.response ({lang}) missing safety-first reference to emergency services"
    )
