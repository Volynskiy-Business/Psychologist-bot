"""Deterministic response quality check for support dialogue.

Detects robotic, clinical, or prematurely-escalating patterns before they reach
the user. Used in the pipeline to decide whether a humanization rewrite is needed.
"""

from dataclasses import dataclass

from app.ai.orchestration.models import RiskTier

# Specialist referral phrases — premature at Tier 0-1
_PREMATURE_REFERRAL_RU: list[str] = [
    "обратись к специалисту",
    "обратитесь к специалисту",
    "к психологу",
    "к психотерапевту",
    "к психиатру",
    "к врачу",
    "профессиональная помощь",
    "обратись за профессиональной",
    "обратитесь за профессиональной",
    "квалифицированному специалисту",
]
_PREMATURE_REFERRAL_EN: list[str] = [
    "seek professional help",
    "contact a specialist",
    "see a therapist",
    "see a psychologist",
    "reach out to a professional",
    "professional support",
    "qualified specialist",
    "mental health professional",
    "therapist or counselor",
    "therapist or counsellor",
]

# Emergency language phrases — wrong tier for Tier 0-1
_EMERGENCY_LANGUAGE_RU: list[str] = [
    "экстренные службы",
    "кризисная линия",
    "скорую помощь",
    "экстренную помощь",
    "номер экстренной",
    "немедленно обратитесь",
    "немедленно обратись",
]
_EMERGENCY_LANGUAGE_EN: list[str] = [
    "emergency services",
    "crisis line",
    "crisis hotline",
    "emergency helpline",
    "call 911",
    "call 999",
    "call 112",
]

# AI identity phrases — never appropriate
_AI_IDENTITY: list[str] = [
    "как ии",
    "как ai",
    "as an ai",
    "as an artificial intelligence",
    "being an ai",
    "будучи ии",
    "я — ии",
    "i'm an ai",
    "i am an ai",
]

# Clinical/diagnostic language — inappropriate in companion context
_CLINICAL_RU: list[str] = [
    "клинические симптомы",
    "поставить диагноз",
    "диагностировать",
    "медицинский диагноз",
]
_CLINICAL_EN: list[str] = [
    "clinical symptoms",
    "clinical diagnosis",
    "diagnosing you",
    "medical diagnosis",
]


@dataclass
class ResponseQualityResult:
    premature_referral: bool = False
    emergency_language_mismatch: bool = False
    ai_identity_leak: bool = False
    too_clinical: bool = False

    @property
    def should_rewrite(self) -> bool:
        return (
            self.premature_referral
            or self.emergency_language_mismatch
            or self.ai_identity_leak
            or self.too_clinical
        )

    def issues(self) -> str:
        found = [
            name
            for name, flag in [
                ("premature_referral", self.premature_referral),
                ("emergency_language_mismatch", self.emergency_language_mismatch),
                ("ai_identity_leak", self.ai_identity_leak),
                ("too_clinical", self.too_clinical),
            ]
            if flag
        ]
        return ",".join(found) or "none"


def check_response_quality(response: str, risk_tier: RiskTier) -> ResponseQualityResult:
    """Return quality issues found in the response for the given risk tier."""
    t = response.lower()

    ai_identity_leak = any(p in t for p in _AI_IDENTITY)
    too_clinical = any(p in t for p in _CLINICAL_RU + _CLINICAL_EN)

    has_referral = any(p in t for p in _PREMATURE_REFERRAL_RU + _PREMATURE_REFERRAL_EN)
    premature_referral = has_referral and risk_tier.value <= 1

    has_emergency = any(p in t for p in _EMERGENCY_LANGUAGE_RU + _EMERGENCY_LANGUAGE_EN)
    emergency_language_mismatch = has_emergency and risk_tier.value <= 1

    return ResponseQualityResult(
        premature_referral=premature_referral,
        emergency_language_mismatch=emergency_language_mismatch,
        ai_identity_leak=ai_identity_leak,
        too_clinical=too_clinical,
    )
