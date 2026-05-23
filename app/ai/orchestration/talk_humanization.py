"""Deterministic quality checker for Talk Mode (Поговорить) responses.

Scores responses for human-conversational quality without LLM calls.
A low score signals that the response sounds mechanical, therapeutic, or
generic — and triggers one LLM repair pass in FriendlyConversationAgent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Forbidden phrase patterns (lower the score) ───────────────────────────────

_GENERIC_VALIDATION_RU: list[str] = [
    r"я понимаю,?\s+как",
    r"я слышу,?\s+что",
    r"слышу,?\s+что (тебе|вам)",          # variant without "я"
    r"(твои|ваши) чувства (важны|понятны|нормальны|оправданы)",
    r"это (совершенно )?нормально (чувствовать|ощущать)",
    r"это нормально чувствовать",
    r"важно,?\s+что ты",
    r"важно,?\s+что вы",
    r"спасибо,?\s+что поделил",
    r"что именно (тебя|вас|тебе) беспокоит",
    r"мне очень жаль слышать",
    r"это (тяжёлое|тяжелое) чувство",
    r"это чувство может быть",
    r"это совершенно понятно в такой ситуации",
    r"это долгий и непростой путь",
    r"каждый шаг может казаться",
    r"это совершенно (нормально|понятно)",
    r"звучит так,?\s+будто (ты|вы) чувствуешь",
    r"ты чувствуешь себя",
    r"очень тяжёлое испытание",
    r"очень тяжелое испытание",
    r"развод — это действительно",
    r"что сейчас для тебя самое (трудное|тяжёлое|тяжелое)",
    r"как ты справляешься с (этими|такими) мыслями",
    r"хочешь рассказать (подробнее|больше|мне)",
]

_GENERIC_VALIDATION_EN: list[str] = [
    r"i understand how (difficult|hard|painful|tough)",
    r"i hear that",
    r"your feelings are valid",
    r"it('?s| is) (perfectly |only |completely )?normal to feel",
    r"it is important that you (shared|told|opened)",
    r"thank you for sharing",
    r"what exactly (worries|bothers|concerns) you",
    r"let'?s explore",
    r"sounds like you('?re| are) feeling",
]

_THERAPY_JARGON: list[str] = [
    "копинг",
    "coping mechanism",
    "эмоциональн",  # эмоциональная регуляция
    "emotional regulation",
    "техника заземлени",
    "grounding technique",
    "когнитивн",
    "cognitive",
    "травматическ",
    "trauma response",
    "поведенческ",
    "behavioral activation",
    "дбт",
    "дbt",
    " dbt ",
    "акт терапи",
    " act therapy",
]

_MARKDOWN_RE = re.compile(r"[*_`#]|\*\*|__")
_SENTENCE_END_RE = re.compile(r"[.!?…]+\s")
_QUESTION_RE = re.compile(r"\?")

_REPAIR_SCORE_THRESHOLD = 60


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class TalkHumanizationResult:
    score: int
    flags: list[str] = field(default_factory=list)
    question_count: int = 0
    sentence_count: int = 0
    has_generic_validation: bool = False
    has_therapy_jargon: bool = False
    has_markdown: bool = False
    too_long: bool = False
    too_many_questions: bool = False
    lacks_specific_anchor: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────


def _count_sentences(text: str) -> int:
    # Count sentence-ending punctuation followed by whitespace, plus the final sentence
    return max(1, len(_SENTENCE_END_RE.findall(text + " ")))


def _count_questions(text: str) -> int:
    return len(_QUESTION_RE.findall(text))


def _check_patterns(text: str, patterns: list[str]) -> list[str]:
    lower = text.lower()
    return [p for p in patterns if re.search(p, lower)]


def _has_specific_anchor(text: str, user_message: str) -> bool:
    """True if the response echoes at least one content word from the user's message."""
    words = [w for w in re.findall(r"\w+", user_message.lower()) if len(w) >= 2]
    if not words:
        return True  # short/empty message — don't penalize
    text_lower = text.lower()
    return any(w in text_lower for w in words)


# ── Public API ────────────────────────────────────────────────────────────────


def score_talk_humanness(text: str, user_message: str) -> TalkHumanizationResult:
    """Score a Talk Mode response for conversational naturalness (0–100)."""
    score = 100
    flags: list[str] = []

    sentence_count = _count_sentences(text)
    question_count = _count_questions(text)

    # Markdown
    has_md = bool(_MARKDOWN_RE.search(text))
    if has_md:
        score -= 15
        flags.append("markdown")

    # Generic validation phrases
    ru_hits = _check_patterns(text, _GENERIC_VALIDATION_RU)
    en_hits = _check_patterns(text, _GENERIC_VALIDATION_EN)
    has_generic = bool(ru_hits or en_hits)
    if has_generic:
        penalty = 15 * min(len(ru_hits) + len(en_hits), 3)
        score -= penalty
        flags.extend(ru_hits[:2])
        flags.extend(en_hits[:1])

    # Therapy jargon
    text_lower = text.lower()
    jargon_hits = [kw for kw in _THERAPY_JARGON if kw in text_lower]
    has_jargon = bool(jargon_hits)
    if has_jargon:
        score -= 20
        flags.append(f"therapy_jargon:{jargon_hits[0]}")

    # Multiple questions (interview style)
    too_many_q = question_count > 1
    if too_many_q:
        score -= 30
        flags.append(f"too_many_questions:{question_count}")

    # Too long
    too_long = sentence_count > 5
    if too_long:
        score -= 20
        flags.append(f"too_long:{sentence_count}_sentences")

    # No concrete echo of user's words
    lacks_anchor = not _has_specific_anchor(text, user_message)
    if lacks_anchor:
        score -= 10
        flags.append("no_specific_anchor")

    return TalkHumanizationResult(
        score=max(0, score),
        flags=flags,
        question_count=question_count,
        sentence_count=sentence_count,
        has_generic_validation=has_generic,
        has_therapy_jargon=has_jargon,
        has_markdown=has_md,
        too_long=too_long,
        too_many_questions=too_many_q,
        lacks_specific_anchor=lacks_anchor,
    )


def should_repair_talk_response(result: TalkHumanizationResult) -> bool:
    """Return True when the response is mechanical enough to warrant an LLM repair."""
    return result.score < _REPAIR_SCORE_THRESHOLD


def humanize_talk_response(text: str, _user_message: str) -> str:
    """Deterministic fallback cleanup: strip Markdown only.

    Called when the LLM repair pass itself fails. Keeps the meaning intact
    while removing the most visually jarring formatting artifact.
    """
    return _MARKDOWN_RE.sub("", text).strip()
