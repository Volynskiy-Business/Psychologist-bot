"""Sadness Support sub-agent — RAG-powered conversational support for sadness and grief.

Retrieves the 1-2 most relevant scenarios from the sadness knowledge base via TF-IDF
cosine similarity, then injects them into the system prompt as contextual guidance.

Knowledge base: app/knowledge/sadness_support.py (15 evidence-based scenarios)
Vector store:   app/knowledge/vector_store.py (TF-IDF, no external ML deps)

Design:
- Six-phase conversation architecture: invite → presence → validate → meaning → activate → follow-up.
- Behavioral Activation (BA): one small, doable action — not 'fix everything now'.
- Empathy-first: validate before advising.
- Escalation check for hopelessness / meaninglessness scenarios.
- Temperature 0.45 — warm and focused, not clinical.
"""

import logging
from typing import Optional

from app.ai.openrouter_client import OpenRouterClient
from app.ai.orchestration.models import PipelineResult, RiskTier
from app.ai.output_validation import validate_support_response
from app.ai.prompts.humanization_prompt import build_humanization_prompt
from app.ai.response_quality import check_response_quality
from app.knowledge.sadness_support import SadnessScenario
from app.knowledge.vector_store import sadness_store

logger = logging.getLogger(__name__)

_BASE_PROMPT = """Ты — поддерживающий собеседник для человека, переживающего грусть, тоску, горе или подавленность.

Ты не врач и не психотерапевт. Не называй себя специалистом. Не говори «как ИИ» — просто отвечай.

━━━ ЖЁСТКИЕ ЗАПРЕТЫ ━━━
• Не ставь диагнозы, не называй расстройства.
• Не назначай и не комментируй лекарства.
• Не давай инструкции по самоповреждению или насилию.
• Не давай безоговорочных обещаний («всё будет хорошо», «скоро пройдёт»).
• Не форсируй позитив до того, как человек почувствовал себя услышанным.

━━━ ШЕСТЬ ФАЗ ДИАЛОГА ━━━
1. Приглашение — спроси с разрешения, создай безопасность.
2. Присутствие — замедли темп, не торопи, снизи давление.
3. Валидация — подтверди, что грусть понятна в контексте.
4. Смысл — мягко исследуй, с чем связана грусть.
5. Активация — один маленький конкретный шаг навстречу облегчению.
6. Контакт — напомни, что ты рядом и можно продолжить.

━━━ ПОВЕДЕНЧЕСКАЯ АКТИВАЦИЯ (BA) ━━━
При подавленности и апатии — задавай вопросы в логике BA:
• «Что раньше хоть немного помогало?»
• «Какое одно действие возможно в следующие 30 минут?»
• «Самая маленькая версия этого — что это?»
• Цель не «быть продуктивным», а «восстановить движение».
При тяжёлом состоянии — предлагай минимальные действия: душ, вода, прогулка, один звонок.

━━━ ЧТО НЕ ДЕЛАТЬ ━━━
• «Просто будь позитивным» — обесценивает.
• «У других хуже» — вызывает стыд.
• «Ты слишком чувствительный» — усиливает изоляцию.
• «Соберись» — игнорирует реальное истощение.
• Форсировать решение до того, как человек почувствовал себя понятым.

━━━ КОГДА УПОМИНАТЬ ПРОФЕССИОНАЛЬНУЮ ПОМОЩЬ ━━━
Мягко и без давления, если:
• грусть длится более двух недель,
• нарушается ежедневное функционирование,
• человек сам спрашивает о специалисте.
Немедленно переходи к кризисной поддержке при сигналах об угрозе жизни.

{scenario_guidance}

━━━ СТИЛЬ ━━━
Тёплый, конкретный, земной. Без клише и клинических терминов.
Объём: 3–7 предложений. Максимум один вопрос в конце.
Только обычный текст — никакого Markdown.
Отвечай строго на языке ТЕКУЩЕГО сообщения пользователя: «{lang}»."""


def _format_scenario_guidance(scenarios: list[SadnessScenario]) -> str:
    if not scenarios:
        return ""
    lines = ["━━━ РЕЛЕВАНТНЫЕ РУКОВОДСТВА ━━━"]
    for i, s in enumerate(scenarios, 1):
        lines.append(f"\n**Сценарий {i}: {s.title_ru}**")
        lines.append(f"Когда применять: {s.context_description_ru}")
        lines.append(f"Полезные фразы: {' / '.join(s.helpful_phrases[:3])}")
        lines.append(f"Фразы-ловушки: {' / '.join(s.harmful_phrases[:3])}")
        lines.append(f"Подход: {s.conversation_approach}")
        if s.escalation_check:
            lines.append(
                "⚠ ВАЖНО: Прямо спроси о безопасности ('бывают ли мысли о том, "
                "чтобы причинить себе вред?'). При утвердительном ответе — кризисная реакция."
            )
    return "\n".join(lines)


class SadnessSupportAgent:
    """RAG-powered agent for sadness, grief, and low mood support.

    At each call: retrieves the top-2 most relevant scenarios from the
    sadness knowledge base via TF-IDF cosine similarity, then injects
    their guidance into the system prompt.
    """

    def __init__(self, client: OpenRouterClient, model: Optional[str] = None) -> None:
        self.client = client
        self.model = model

    def build_prompt(self, user_text: str, lang: str) -> str:
        relevant = sadness_store.search(user_text, top_k=2)
        scenario_guidance = _format_scenario_guidance(relevant)
        return _BASE_PROMPT.format(scenario_guidance=scenario_guidance, lang=lang)

    async def run(
        self,
        user_text: str,
        lang: str,
        history: list[dict[str, str]],
    ) -> PipelineResult:
        logger.debug("stage=sadness_support lang=%s", lang)

        system_prompt = self.build_prompt(user_text, lang)
        messages: list[dict[str, str]] = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": user_text}]
        )

        response = await self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.45,
            max_tokens=600,
        )
        draft = response.content

        quality = check_response_quality(draft, RiskTier.TIER_1)
        if quality.should_rewrite:
            logger.info("stage=sadness_support_rewrite issues=%s", quality.issues())
            try:
                humanization_prompt = build_humanization_prompt(draft, user_text, lang)
                rewrite = await self.client.chat_completion(
                    messages=[{"role": "user", "content": humanization_prompt}],
                    model=self.model,
                    temperature=0.3,
                    max_tokens=500,
                )
                draft = rewrite.content
            except Exception:
                logger.exception(
                    "stage=sadness_support_rewrite failed; using original draft"
                )

        is_safe, block_reason = validate_support_response(draft)
        if not is_safe:
            logger.warning(
                "stage=sadness_support_validation blocked reason=%s", block_reason
            )

        return PipelineResult(
            content=draft,
            is_safe=is_safe,
            block_reason=block_reason,
            scenario_id="sadness_support",
            technique_id=None,
            risk_tier=RiskTier.TIER_1,
            intake_language=lang,
        )
