"""Tests for safety_protocols.get_crisis_response.

Pins that:
- Each supported locale returns a non-empty crisis response for both
  POSSIBLE_CRISIS and IMMINENT_RISK risk levels.
- NO_RISK / MILD_DISTRESS / ELEVATED_DISTRESS deliberately return empty —
  protocol routing is the caller's job for those levels.
"""

from pathlib import Path

import pytest

from app.db.models import RiskLevel
from app.safety.safety_protocols import get_crisis_response

I18N_DIR = Path(__file__).resolve().parent.parent.parent / "i18n"
SUPPORTED_LOCALES = sorted(p.stem for p in I18N_DIR.glob("*.json"))


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
@pytest.mark.parametrize(
    "risk_level",
    [RiskLevel.POSSIBLE_CRISIS, RiskLevel.IMMINENT_RISK],
)
def test_crisis_response_non_empty_per_locale(
    locale: str, risk_level: RiskLevel
) -> None:
    text = get_crisis_response(risk_level, locale)
    assert isinstance(text, str)
    assert text.strip(), (
        f"locale={locale} risk={risk_level.name} returned empty crisis response"
    )


@pytest.mark.parametrize(
    "risk_level",
    [RiskLevel.NO_RISK, RiskLevel.MILD_DISTRESS, RiskLevel.ELEVATED_DISTRESS],
)
def test_non_crisis_levels_return_empty(risk_level: RiskLevel) -> None:
    """Below POSSIBLE_CRISIS the protocol returns empty — the caller decides
    how to handle elevated distress (e.g. soft check-in flow)."""
    assert get_crisis_response(risk_level, "en") == ""


def test_unknown_locale_falls_back_to_english() -> None:
    """The i18n layer falls back to English for unknown locales, so the
    crisis response must still be non-empty rather than the raw key."""
    text = get_crisis_response(RiskLevel.IMMINENT_RISK, "xx")
    assert text.strip()
    assert text != "crisis.response"
