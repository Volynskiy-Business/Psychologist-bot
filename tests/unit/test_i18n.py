"""Key-parity and content-safety checks for i18n translations.

Mental-health bots cannot ship with locales that silently fall back to a
different language for crisis/disclaimer strings, so this file enforces:

1. Every locale exposes the same set of leaf keys as ``en.json``.
2. Safety-critical namespaces (``crisis``, ``start.disclaimer``,
   ``start.crisis_warning``) exist and are non-empty in every locale.
3. Crisis responses are non-trivial (length floor) so an empty string can't
   slip through review.
"""

import json
from pathlib import Path
from typing import Any

import pytest

I18N_DIR = Path(__file__).resolve().parent.parent.parent / "i18n"
REFERENCE_LOCALE = "en"

# Keys that must exist and be non-empty in every locale. Adding to this list
# expands the safety floor; removing should be reviewed carefully.
SAFETY_REQUIRED_KEYS: tuple[str, ...] = (
    "crisis.response",
    "crisis.elevated",
    "start.disclaimer",
    "start.crisis_warning",
    "chat.error",
)


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Return a flat ``{dotted.key: leaf_value}`` map of a nested dict.

    Lists are kept as leaves so we don't accidentally require list ordering
    parity at the index level; we just require the same set of keys.
    """
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            child = f"{prefix}.{k}" if prefix else k
            out.update(_flatten(v, child))
    else:
        out[prefix] = value
    return out


def _load(locale: str) -> dict[str, Any]:
    with open(I18N_DIR / f"{locale}.json", encoding="utf-8") as f:
        return json.load(f)


def _locales() -> list[str]:
    return sorted(p.stem for p in I18N_DIR.glob("*.json"))


def test_reference_locale_exists() -> None:
    assert (I18N_DIR / f"{REFERENCE_LOCALE}.json").exists(), (
        f"Reference locale {REFERENCE_LOCALE}.json must exist"
    )


@pytest.mark.parametrize("locale", _locales())
def test_locale_has_same_keys_as_reference(locale: str) -> None:
    ref = set(_flatten(_load(REFERENCE_LOCALE)).keys())
    actual = set(_flatten(_load(locale)).keys())
    missing = ref - actual
    extra = actual - ref
    assert not missing, f"{locale}.json missing keys: {sorted(missing)}"
    assert not extra, f"{locale}.json has unexpected keys: {sorted(extra)}"


@pytest.mark.parametrize("locale", _locales())
@pytest.mark.parametrize("key", SAFETY_REQUIRED_KEYS)
def test_safety_keys_non_empty(locale: str, key: str) -> None:
    flat = _flatten(_load(locale))
    assert key in flat, f"{locale}.json is missing safety key {key!r}"
    value = flat[key]
    assert isinstance(value, str) and value.strip(), (
        f"{locale}.json has empty safety value for {key!r}"
    )


@pytest.mark.parametrize("locale", _locales())
def test_crisis_response_is_substantive(locale: str) -> None:
    """Crisis responses must be more than a stub — short strings here are
    almost certainly a translation oversight."""
    flat = _flatten(_load(locale))
    response = flat["crisis.response"]
    elevated = flat["crisis.elevated"]
    # 80 chars is a conservative floor — even terse languages produce more
    # than this for a multi-step crisis instruction.
    assert len(response) >= 80, f"{locale} crisis.response looks truncated: {response!r}"
    assert len(elevated) >= 80, f"{locale} crisis.elevated looks truncated: {elevated!r}"
