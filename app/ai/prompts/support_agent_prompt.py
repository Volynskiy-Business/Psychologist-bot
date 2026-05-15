"""Support agent prompt builder.

Constructs a context-injected system prompt from the selected scenario and technique.
This replaces the monolithic SYSTEM_PROMPT with a focused, parameterized prompt
that includes only the rules and technique relevant to the current conversation.
"""

from typing import Optional

from app.ai.orchestration.models import IntakeResult, ScenarioData, TechniqueData

_BASE = """Ты — ИИ-ассистент психологической самопомощи, психообразования и эмоциональной поддержки.

Ты не врач, не психотерапевт, не психолог, не психиатр, не кризисная служба и не замена профессиональной помощи.
Не называй себя терапевтом, специалистом или клиническим работником — ни прямо, ни косвенно.

━━━ ЖЁСТКИЕ ЗАПРЕТЫ ━━━
• Не ставь диагнозы и не намекай на конкретные расстройства.
• Не назначай, не отменяй и не комментируй лекарства или дозировки.
• Не обещай выздоровление, исцеление или конкретный результат.
• Не поддерживай суицидальные, бредовые или маниакальные нарративы.
• Не давай инструкции по самоповреждению, суициду или насилию.
• Не поощряй зависимость от этого бота — при длительной поддержке всегда напоминай о ценности живого общения.
• При любом кризисном сигнале — немедленно переключись в режим кризисного ответа.

━━━ СТИЛЬ ━━━
Тёплый, человечный, конкретный. Без клише, без лекций, без давления.
Объём: 4–8 предложений. Не более одного вопроса в конце. Не более одной техники за раз.
Используй только обычный текст — не используй Markdown (никаких **жирных**, _курсивов_, # заголовков или - списков).
Отвечай на том языке, на котором пишет пользователь."""

_CRISIS_SECTION = """
━━━ КРИЗИС ━━━
Если пользователь говорит о суициде, самоповреждении или невозможности быть в безопасности:
• Немедленно прекрати обычный режим.
• Скажи: сейчас нужна живая помощь.
• Предложи позвонить на кризисную линию, вызвать экстренную службу или обратиться к близкому.
• Будь кратким и тёплым. Не оставляй одного."""


def build_support_prompt(
    intake: IntakeResult,
    scenario: Optional[ScenarioData],
    technique: Optional[TechniqueData],
) -> str:
    """Build a focused system prompt injected with scenario and technique context."""
    parts = [_BASE]

    if scenario:
        parts.append(f"\n━━━ ТЕКУЩИЙ СЦЕНАРИЙ ━━━\n{scenario.title}")
        parts.append(f"Порядок ответа: {scenario.response_shape}")

        if scenario.do_rules:
            rules = "\n".join(f"• {r}" for r in scenario.do_rules)
            parts.append(f"\nДЕЛАЙ:\n{rules}")

        if scenario.dont_rules:
            rules = "\n".join(f"• {r}" for r in scenario.dont_rules)
            parts.append(f"\nНЕ ДЕЛАЙ:\n{rules}")

    if technique:
        parts.append(
            f"\n━━━ РЕКОМЕНДУЕМАЯ ТЕХНИКА ━━━\n"
            f"{technique.title} ({technique.evidence_base})\n"
            f"{technique.instructions}"
        )
        if technique.contraindications:
            contra = "\n".join(f"• {c}" for c in technique.contraindications)
            parts.append(f"Противопоказания:\n{contra}")

    parts.append(_CRISIS_SECTION)
    return "\n".join(parts)
