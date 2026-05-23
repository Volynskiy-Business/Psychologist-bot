"""OnboardingAgent — conversational onboarding with LLM-based profile extraction.

Conducts a warm 2-step introduction after consent:
  Step 1: asks the user's name and country of residence
  Step 2: asks preferred consultant gender

After each step, runs an ExtractorAgent (fast LLM call) to parse free-form
answers into structured profile fields stored in PostgreSQL.

The two AI consultant personas (female + male) are assigned names based on
the user's detected country so they feel culturally familiar.
"""

import json
import logging
import re
from typing import Optional

from app.ai.openrouter_client import OpenRouterClient
from app.ai.orchestration.models import RiskTier
from app.ai.prompts.humanization_prompt import build_humanization_prompt
from app.ai.response_quality import check_response_quality

logger = logging.getLogger(__name__)

# ── Country → Consultant name mapping ────────────────────────────────────────
# (female_name, male_name) based on popular names in each country

_COUNTRY_NAMES: dict[str, tuple[str, str]] = {
    # Russia / СНГ
    "россия": ("Мария", "Максим"),
    "russia": ("Мария", "Максим"),
    "rf": ("Мария", "Максим"),
    "украина": ("Олена", "Олексій"),
    "ukraine": ("Олена", "Олексій"),
    "беларусь": ("Алёна", "Алексей"),
    "belarus": ("Алёна", "Алексей"),
    "казахстан": ("Айгерим", "Арман"),
    "kazakhstan": ("Айгерим", "Арман"),
    # Israel
    "израиль": ("Нoа", "Ноам"),
    "israel": ("Нoа", "Ноам"),
    # German-speaking
    "германия": ("Мари", "Макс"),
    "germany": ("Мари", "Макс"),
    "австрия": ("Мари", "Макс"),
    # Scandinavia / Western Europe fallback
    "норвегия": ("Лив", "Матиас"),
    "дания": ("Сигне", "Николай"),
    # English-speaking
    "сша": ("Мia", "Макс"),
    "usa": ("Мia", "Макс"),
    "великобритания": ("Оливия", "Оливер"),
    "uk": ("Оливия", "Оливер"),
}

# Language-code fallback (used before country is known)
_LANG_NAMES: dict[str, tuple[str, str]] = {
    "ru": ("Мария", "Максим"),
    "en": ("Maria", "Max"),
    "de": ("Marie", "Max"),
    "fr": ("Marie", "Maxime"),
    "no": ("Лив", "Матиас"),
    "da": ("Сигне", "Николай"),
    "pt": ("Ana", "João"),
    "es": ("Sofía", "Carlos"),
    "_default": ("Мария", "Максим"),
}


def get_consultant_names(country: Optional[str], lang: str = "ru") -> tuple[str, str]:
    """Return (female_name, male_name) for given country/lang."""
    if country:
        normalized = country.strip().lower()
        # Try exact match, then partial match
        for key, names in _COUNTRY_NAMES.items():
            if key in normalized or normalized in key:
                return names
    return _LANG_NAMES.get(lang, _LANG_NAMES["_default"])


# ── Prompt templates ──────────────────────────────────────────────────────────

_GENDER_FEMALE = (
    "Ты говоришь строго от ЖЕНСКОГО лица. "
    "Используй только женские формы: «я рада», «я познакомилась», «я подумала», «я готова», «я хотела»."
)
_GENDER_MALE = (
    "Ты говоришь строго от МУЖСКОГО лица. "
    "Используй только мужские формы: «я рад», «я познакомился», «я подумал», «я готов», «я хотел»."
)

_STEP1_SYSTEM = """Ты — {consultant_name}, AI-консультант для эмоциональной поддержки и самопомощи. Твой коллега — {colleague_name}.
{gender_instruction}
Ты только что встретил(-а) нового пользователя — он принял условия использования и теперь ты хочешь узнать его немного получше.

Напиши короткое тёплое приветствие от своего имени.
В нём мягко и нативно спроси пользователя:
- Как его зовут (или как к нему можно обращаться)
- Где он сейчас живёт (страна)

Важно:
- Не называй себя врачом, терапевтом, клиническим специалистом или лицензированным профессионалом.
- Если нужно обозначить роль, говори: «AI-консультант для эмоциональной поддержки».
- Не упоминай технологии, серверы, алгоритмы.
- Не спрашивай о проблемах и не начинай консультацию — только знакомство.
- Тон: тёплый, живой, без формальностей. 2–3 предложения максимум.
- Только обычный текст, никакого Markdown.
- Язык: {lang}."""

_STEP2_SYSTEM = """Ты — {consultant_name}, AI-консультант для эмоциональной поддержки и самопомощи.
{gender_instruction}
Ты уже познакомился(-ась) с пользователем и знаешь его немного.
Теперь тебе нужно мягко узнать, с кем пользователю будет комфортнее общаться — с тобой ({consultant_name}) или с твоим коллегой ({colleague_name}).

Напиши одно тёплое предложение, представь своего коллегу по имени ({colleague_name}) и спроси, с кем пользователю комфортнее.
Не называй себя или коллегу врачом, терапевтом, клиническим специалистом или лицензированным профессионалом.
Тон: лёгкий, без давления, с пониманием что это личный выбор и оба варианта хороши.
Никакого Markdown. 1–2 предложения. Язык: {lang}."""

_STEP2_WITH_NAME_SYSTEM = """Ты — {consultant_name}, AI-консультант для эмоциональной поддержки и самопомощи.
{gender_instruction}
Ты уже познакомился(-ась) с пользователем по имени {user_name}.
Теперь нужно мягко узнать, с кем {user_name} будет комфортнее общаться — с тобой ({consultant_name}) или с твоим коллегой ({colleague_name}).

Напиши одно тёплое предложение: обратись по имени к пользователю, представь своего коллегу ({colleague_name}) и спроси, с кем комфортнее.
Не называй себя или коллегу врачом, терапевтом, клиническим специалистом или лицензированным профессионалом.
Никакого Markdown. 1–2 предложения. Язык: {lang}."""

_DONE_SYSTEM = """Ты — {consultant_name}, AI-консультант для эмоциональной поддержки и самопомощи.
{gender_instruction}
Пользователь только что завершил краткое знакомство. Напиши одну тёплую фразу (без вопросов),
которая даёт понять что ты рад(-а) знакомству и готов(-а) общаться.
Не называй себя врачом, терапевтом, клиническим специалистом или лицензированным профессионалом.
Если знаешь имя пользователя — обратись по имени. Не спрашивай ни о чём — только тёплое завершение знакомства.
Никакого Markdown. 1 предложение. Язык: {lang}."""

# ── Extractor prompt ──────────────────────────────────────────────────────────

_EXTRACTOR_PROMPT = """Из следующего сообщения пользователя извлеки данные в JSON.

Правила:
- "name": имя или псевдоним пользователя, null если не упомянуто
- "gender": пол пользователя — "male", "female", "other", или "unknown"
  Определяй ТОЛЬКО по: форме глаголов/прилагательных ("устал"→male, "устала"→female),
  местоимениям ("я сам"→male, "я сама"→female), прямому указанию ("я мужчина"/"я женщина").
  НЕ угадывай пол по имени — если явного сигнала нет, используй "unknown".
- "country": страна проживания строкой (например "Израиль", "Россия"), null если не упомянуто
- "consultant_gender": предпочтение консультанта — "male", "female", "any", или "unknown"
  "female" если: "женщина", "девушка", "с тобой", "Мария", "{female_name}", "мне комфортнее с женщиной" и т.п.
  "male" если: "мужчина", "парень", "коллега", "{male_name}", "с мужчиной" и т.п.
  "any" если: "не важно", "всё равно", "без разницы", "оба", "любой"

Отвечай ТОЛЬКО валидным JSON, без markdown-блоков, без пояснений.

Сообщение пользователя:
"{text}"
"""


class OnboardingAgent:
    """Two-step conversational onboarding agent with LLM profile extraction."""

    def __init__(self, client: OpenRouterClient, model: Optional[str] = None) -> None:
        self.client = client
        self.model = model

    async def _maybe_humanize(self, draft: str, lang: str) -> str:
        """Run quality check; if needed, rewrite draft through humanizer."""
        quality = check_response_quality(draft, RiskTier.TIER_1)
        if not quality.should_rewrite:
            return draft
        logger.info("stage=onboarding_humanize issues=%s", quality.issues())
        try:
            humanization_prompt = build_humanization_prompt(draft, "", lang)
            rewrite = await self.client.chat_completion(
                messages=[{"role": "user", "content": humanization_prompt}],
                model=self.model,
                temperature=0.3,
                max_tokens=300,
            )
            return rewrite.content.strip()
        except Exception:
            logger.exception("stage=onboarding_humanize failed; using original draft")
            return draft

    async def start_message(
        self,
        lang: str,
        female_name: str,
        male_name: str,
        consultant_gender: str,  # initial default = "female"
    ) -> str:
        """Generate the first warm greeting message (Step 1)."""
        if consultant_gender == "male":
            consultant_name, colleague_name = male_name, female_name
            gender_instruction = _GENDER_MALE
        else:
            consultant_name, colleague_name = female_name, male_name
            gender_instruction = _GENDER_FEMALE

        system = _STEP1_SYSTEM.format(
            consultant_name=consultant_name,
            colleague_name=colleague_name,
            gender_instruction=gender_instruction,
            lang=lang,
        )
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "Начни знакомство."}],
            model=self.model,
            temperature=0.6,
            max_tokens=200,
        )
        return await self._maybe_humanize(response.content.strip(), lang)

    async def step2_message(
        self,
        lang: str,
        female_name: str,
        male_name: str,
        consultant_gender: str,
        user_name: Optional[str],
    ) -> str:
        """Generate the second question about consultant gender preference."""
        if consultant_gender == "male":
            consultant_name, colleague_name = male_name, female_name
            gender_instruction = _GENDER_MALE
        else:
            consultant_name, colleague_name = female_name, male_name
            gender_instruction = _GENDER_FEMALE

        if user_name:
            system = _STEP2_WITH_NAME_SYSTEM.format(
                consultant_name=consultant_name,
                colleague_name=colleague_name,
                user_name=user_name,
                gender_instruction=gender_instruction,
                lang=lang,
            )
        else:
            system = _STEP2_SYSTEM.format(
                consultant_name=consultant_name,
                colleague_name=colleague_name,
                gender_instruction=gender_instruction,
                lang=lang,
            )
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "Задай вопрос."}],
            model=self.model,
            temperature=0.6,
            max_tokens=150,
        )
        return await self._maybe_humanize(response.content.strip(), lang)

    async def done_message(
        self,
        lang: str,
        consultant_name: str,
        consultant_gender: str,
        user_name: Optional[str],
    ) -> str:
        """Generate a warm closing line after onboarding is complete."""
        gender_instruction = _GENDER_MALE if consultant_gender == "male" else _GENDER_FEMALE
        system = _DONE_SYSTEM.format(
            consultant_name=consultant_name,
            gender_instruction=gender_instruction,
            user_name=user_name or "",
            lang=lang,
        )
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "Заверши знакомство."}],
            model=self.model,
            temperature=0.6,
            max_tokens=100,
        )
        return await self._maybe_humanize(response.content.strip(), lang)

    async def extract_profile(
        self,
        user_text: str,
        female_name: str,
        male_name: str,
    ) -> dict:
        """Extract structured profile data from free-form user text.

        Returns dict with keys: name, gender, country, consultant_gender.
        All values may be None / "unknown".
        """
        prompt = _EXTRACTOR_PROMPT.format(
            text=user_text,
            female_name=female_name,
            male_name=male_name,
        )
        try:
            response = await self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.0,
                max_tokens=200,
            )
            raw = response.content.strip()
            # Strip markdown code fences if model added them
            raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
            data = json.loads(raw)
            return {
                "name": data.get("name") or None,
                "gender": data.get("gender") or "unknown",
                "country": data.get("country") or None,
                "consultant_gender": data.get("consultant_gender") or "unknown",
            }
        except Exception:
            logger.exception("OnboardingAgent.extract_profile failed")
            return {"name": None, "gender": "unknown", "country": None, "consultant_gender": "unknown"}
