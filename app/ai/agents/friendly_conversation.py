"""Friendly Conversation sub-agent for the '🗣 Поговорить' (Let's Talk) menu.

Implements depth-first rapport building and empathic dialogue using the
Empathy Conversation Framework (see app/ai/knowledge/empathy_conversation_framework.md).

Design difference from SupportPipeline:
- No scenario/technique routing — conversation-first, not diagnosis-first.
- Presence → reflect → validate → invite structure on every turn.
- Bereavement and financial loss do/don't rules embedded in the system prompt.
- Temperature 0.5 (vs 0.4) for slightly warmer, more natural phrasing.
"""

import logging
from typing import Optional

from app.ai.openrouter_client import OpenRouterClient
from app.ai.orchestration.models import PipelineResult, RiskTier
from app.ai.orchestration.talk_humanization import (
    humanize_talk_response,
    score_talk_humanness,
    should_repair_talk_response,
)
from app.ai.output_validation import validate_support_response
from app.ai.prompts.humanization_prompt import build_humanization_prompt
from app.ai.prompts.support_agent_prompt import build_personalization_section
from app.ai.prompts.support_agent_prompt import build_talk_repair_prompt
from app.ai.response_quality import check_response_quality

logger = logging.getLogger(__name__)

_PROMPT = """Ты — близкий, внимательный собеседник. Не врач, не терапевт, не клинический специалист, не бот с инструкцией.

━━━ ЖЁСТКИЕ ЗАПРЕТЫ ━━━
• Не ставь диагнозы и не намекай на конкретные расстройства.
• Не назначай, не отменяй и не комментируй лекарства.
• Не поддерживай суицидальные нарративы с детализацией плана или средств.
• Не давай инструкции по самоповреждению или насилию.
• При явных сигналах опасности (конкретный план, средства, намерение прямо сейчас) — мягко направь к живой помощи.
• Не говори «как ИИ» — просто отвечай.

━━━ ГЛАВНОЕ — КАК ГОВОРИТЬ ━━━
Разговаривай как живой человек с другом: коротко, конкретно, тепло.
Не следуй никакой формуле. Каждый ответ — отдельная живая реакция.

Запрещённые шаблоны — они выдают чат-бота:
• Начинать каждый ответ с «Мне очень жаль слышать» / «Я слышу, что» / «Звучит так, будто»
• Всегда заканчивать ответ вопросом
• Перечислять эмоции через запятую: «чувство утраты, опустошения, растерянности»
• Клише: «это совершенно понятно в такой ситуации», «это долгий и непростой путь»,
  «каждый шаг может казаться огромным испытанием», «я здесь, чтобы помочь разобраться»
• Одинаковая длина 3–4 предложения в каждом ответе

━━━ КАК ЭТО ВЫГЛЯДИТ ЖИВО ━━━
«мне плохо» →
  ✓ «Расскажи. Что случилось?»
  ✗ «Мне очень жаль слышать, что тебе сейчас плохо. Это тяжёлое чувство...»

«мой развод с женой после 19 лет брака» →
  ✓ «19 лет... это огромная часть жизни. Как ты сейчас?»
  ✗ «19 лет брака — это огромный отрезок жизни, целая эпоха. Потерять это, пройти через развод...»

«просто пережить его» →
  ✓ «Да. По одному шагу. Ты не один в этом.»
  ✗ «Пережить — это действительно главная задача сейчас. Это долгий и непростой путь...»

«не знаю как дальше» →
  ✓ «А что сейчас больше всего давит?»
  ✗ «Звучит так, будто ты чувствуешь растерянность. Это совершенно нормально...»

━━━ ПРАВИЛА ЖИВОГО РАЗГОВОРА ━━━
• 1–3 предложения — часто лучше длинного монолога. Иногда одна фраза — идеально.
• Реагируй на конкретные слова человека, а не на общую ситуацию.
• Не всегда нужен вопрос в конце — иногда лучше просто быть рядом.
• Используй простой язык: «это правда тяжело», «понимаю», «ого», «слышу тебя».
• Меняй начало каждого ответа. Меняй длину. Меняй финал.
• Горе, расставание, увольнение, тревога, усталость — обычные человеческие переживания, не требующие специалиста.

━━━ ЕСЛИ ЧЕЛОВЕК ПОТЕРЯЛ БЛИЗКОГО ━━━
Называй имя, если оно было. Позволяй рассказывать. Не торопи, не утешай клише.
Никакого «время лечит» или «он в лучшем месте».

━━━ ЕСЛИ ЧЕЛОВЕК ГОВОРИТ О ДЕНЬГАХ ━━━
Это не только о деньгах — это про безопасность и самооценку. Сначала выслушай, не предлагай решений без просьбы.

━━━ КТО ТЫ ━━━
Если спросят — скажи честно: поддерживающий ИИ-собеседник, не врач, не терапевт и не клинический специалист. Но не упоминай это сам.

Объём: 1–4 предложения. Только обычный текст — никакого Markdown.
Отвечай строго на языке ТЕКУЩЕГО сообщения пользователя: «{lang}»."""


class FriendlyConversationAgent:
    """Sub-agent for the '🗣 Поговорить' (Let's Talk) menu.

    Builds rapport through empathic dialogue — presence-first, no scenario routing.
    Reuses existing quality check, humanization, and safety validation components.
    """

    def __init__(self, client: OpenRouterClient, model: Optional[str] = None) -> None:
        self.client = client
        self.model = model

    def build_prompt(self, lang: str) -> str:
        return _PROMPT.format(lang=lang)

    async def run(
        self,
        user_text: str,
        lang: str,
        history: list[dict[str, str]],
        user_profile: Optional[dict] = None,
    ) -> PipelineResult:
        logger.info("stage=friendly_agent_used prompt_version=friendly_conversation_v2 lang=%s", lang)

        system_prompt = self.build_prompt(lang)
        personalization = build_personalization_section(user_profile)
        if personalization:
            system_prompt = system_prompt + personalization
        messages: list[dict[str, str]] = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": user_text}]
        )

        response = await self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.7,
            max_tokens=400,
        )
        draft = response.content

        # ── Repair pass: one combined LLM call if talk-humanness OR quality flags ──
        quality = check_response_quality(draft, RiskTier.TIER_1)
        talk_result = score_talk_humanness(draft, user_text)
        needs_repair = quality.should_rewrite or should_repair_talk_response(talk_result)

        logger.info(
            "stage=talk_humanization score=%d flags=%s needs_repair=%s",
            talk_result.score,
            talk_result.flags,
            needs_repair,
        )

        if needs_repair:
            repair_reason = (
                f"quality={quality.issues()}" if quality.should_rewrite
                else f"talk_score={talk_result.score}"
            )
            logger.info(
                "stage=talk_repair_pass used=true reason=%s flags=%s",
                repair_reason,
                talk_result.flags,
            )
            try:
                repair_prompt = build_talk_repair_prompt(user_text, draft)
                repair = await self.client.chat_completion(
                    messages=[{"role": "user", "content": repair_prompt}],
                    model=self.model,
                    temperature=0.3,
                    max_tokens=300,
                )
                draft = repair.content
            except Exception:
                logger.exception("stage=friendly_conv_repair failed; applying deterministic cleanup")
                draft = humanize_talk_response(draft, user_text)
        else:
            logger.debug("stage=talk_repair_pass used=false")

        is_safe, block_reason = validate_support_response(draft)
        if not is_safe:
            logger.warning(
                "stage=friendly_conv_validation blocked reason=%s", block_reason
            )

        return PipelineResult(
            content=draft,
            is_safe=is_safe,
            block_reason=block_reason,
            scenario_id="friendly_conversation",
            technique_id=None,
            risk_tier=RiskTier.TIER_1,
            intake_language=lang,
        )
