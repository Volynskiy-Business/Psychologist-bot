"""Deterministic output safety check for LLM responses.

Blocks responses that contain medical authority claims, diagnosis language,
medication management instructions, or self-harm encouragement before they
reach the user.
"""

import re

_BLOCKED_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Identity — claiming to be a doctor or therapist
    (
        re.compile(
            r"\bi\s+am\s+(your\s+)?(doctor|therapist|psychiatrist|psychologist|clinician)\b",
            re.I,
        ),
        "identity_claim",
    ),
    (
        re.compile(
            r"\bas\s+your\s+(doctor|therapist|psychiatrist|psychologist)\b", re.I
        ),
        "identity_claim",
    ),
    # Diagnosis — asserting the user has a named condition
    (
        re.compile(
            r"\byou\s+(?:have|are\s+diagnosed\s+with)\s+(?:\w+\s+){0,3}(?:disorder|syndrome|disease|illness)\b",
            re.I,
        ),
        "diagnosis",
    ),
    # Medication management
    (
        re.compile(
            r"\b(?:stop|discontinue|restart)\s+(?:taking\s+)?(?:your\s+)?(?:medication|medicine|pills?|antidepressants?|antipsychotics?|lithium|sertraline|fluoxetine|olanzapine|risperidone)\b",
            re.I,
        ),
        "medication_instruction",
    ),
    (re.compile(r"\bi\s+(?:can\s+)?prescribe\b", re.I), "prescribing_claim"),
    # Treatment claims
    (re.compile(r"\bi\s+can\s+(?:treat|cure|diagnose)\b", re.I), "treatment_claim"),
    # Self-harm encouragement
    (
        re.compile(
            r"\bit(?:'s|\s+is)\s+(?:okay|fine|alright)\s+to\s+(?:hurt|harm|injure)\s+yourself\b",
            re.I,
        ),
        "self_harm_encouragement",
    ),
]


def validate_support_response(text: str) -> tuple[bool, str | None]:
    """Return (True, None) if the response is safe to send, (False, reason) if blocked."""
    for pattern, reason in _BLOCKED_PATTERNS:
        if pattern.search(text):
            return False, reason
    return True, None
