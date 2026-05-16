"""Deterministic crisis detection with keyword matching."""

import re

from app.db.models import RiskLevel

# Level 2 triggers - passive disappearance / passive death-wish (no stated intent or plan)
# These phrases signal elevated distress but not imminent danger.
LEVEL_2_PATTERNS = [
    # English
    r"\b(wish|want)\b.{0,30}\bdisappear\b",
    r"\bwish\b.{0,30}\bwasn.t here\b",
    r"\bwish\b.{0,30}\bwas not here\b",
    r"\bdon.t want to exist\b",
    r"\bdo not want to exist\b",
    r"\bwant to vanish\b",
    r"\bwant to be gone\b",
    r"\bdon.t want to wake up\b",
    r"\bdo not want to wake up\b",
    r"\bwant to stop existing\b",
    r"\bwish i (had never been|was never) born\b",
    r"\bfeel like disappearing\b",
    r"\bjust want to disappear\b",
    # Russian
    r"\bхочу исчезнуть\b",
    r"\bжелаю исчезнуть\b",
    r"\bне хочу существовать\b",
    r"\bне хочу просыпаться\b",
    r"\bхочу пропасть\b",
    r"\bлучше бы меня не было\b",
    r"\bхотел(а)? бы исчезнуть\b",
    r"\bхочу раствориться\b",
]

# Level 4 triggers - imminent risk
LEVEL_4_PATTERNS = [
    # Russian — explicit intent
    r"\bхочу умереть\b",
    r"\bхочу покончить с собой\b",
    r"\bсобираюсь покончить\b",
    r"\bсобираюсь умереть\b",
    r"\bрешил покончить\b",
    r"\bрешила покончить\b",
    r"\bрешил умереть\b",
    r"\bрешила умереть\b",
    r"\bпланирую суицид\b",
    r"\bу меня есть план\b.*\b(умереть|покончить|свой)\b",
    r"\bсейчас убью\b",
    r"\bсейчас покончу\b",
    r"\bпередозировка\b",
    r"\bвыпил таблеток\b",
    r"\bперерезать вены\b",
    r"\bпрыгнуть с\b",
    r"\bповешусь\b",
    r"\bубью человека\b",
    r"\bхочу убить\b",
    r"\bголоса говорят\b.*\b(убей|умри|сделай)\b",
    r"\bменя контролируют\b.*\b(убить|навредить)\b",
    # English — explicit intent
    r"\bi('m| am) going to (kill myself|end my life|take my (own )?life)\b",
    r"\bi('m| am) going to commit suicide\b",
    r"\bplanning to (kill myself|end my life|commit suicide)\b",
    r"\bi will (kill myself|end my life)\b",
    r"\bgoing to (kill|end|take) my (own )?life\b",
    r"\bhave (pills|a gun|a knife|a rope|the means)\b.{0,60}\b(kill|end|suicide)\b",
    r"\b(kill|end) my (own )?life tonight\b",
    r"\bcommit suicide tonight\b",
    r"\bgoing to hang (myself|myself tonight)\b",
    r"\bgoing to overdose\b",
]

# Level 3 triggers - possible crisis
LEVEL_3_PATTERNS = [
    r"\bне хочу жить\b",
    r"\bне вижу смысла жить\b",
    r"\bлучше бы я умер\b",
    r"\bвсе было бы лучше без меня\b",
    r"\bсамоповреждение\b",
    r"\bрежу себя\b",
    r"\bбью себя\b",
    r"\bпаническая атака\b",
    r"\bне могу дышать\b.*\b(паника|страх)\b",
    r"\bменя преследуют\b",
    r"\bза мной следят\b",
    r"\bменя отравляют\b",
    r"\bне сплю [0-9]+ дней\b",
    r"\bбез сна [0-9]+ дней\b",
    r"\bменя бьют\b",
    r"\bменя избивают\b",
    r"\bнасилие дома\b",
    r"\bизнасиловани[ея]\b",
    r"\bдомашнее насилие\b",
]


def deterministic_crisis_check(text: str) -> tuple[RiskLevel, str | None]:
    """Check text for crisis indicators. Returns (risk_level, matched_pattern)."""
    text_lower = text.lower()

    for pattern in LEVEL_4_PATTERNS:
        if re.search(pattern, text_lower):
            return RiskLevel.IMMINENT_RISK, pattern

    for pattern in LEVEL_3_PATTERNS:
        if re.search(pattern, text_lower):
            return RiskLevel.POSSIBLE_CRISIS, pattern

    for pattern in LEVEL_2_PATTERNS:
        if re.search(pattern, text_lower):
            return RiskLevel.ELEVATED_DISTRESS, pattern

    return RiskLevel.NO_RISK, None
