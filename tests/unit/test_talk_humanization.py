"""Tests for the Talk Mode deterministic humanization scorer."""

import pytest

from app.ai.orchestration.talk_humanization import (
    TalkHumanizationResult,
    humanize_talk_response,
    score_talk_humanness,
    should_repair_talk_response,
)


# ── score_talk_humanness ──────────────────────────────────────────────────────


class TestScoreTalkHumanness:
    def test_clean_response_scores_high(self):
        text = "Расскажи подробнее. Что сейчас больнее всего?"
        result = score_talk_humanness(text, "мне плохо")
        assert result.score >= 80
        assert not result.has_generic_validation
        assert not result.has_therapy_jargon
        assert not result.has_markdown
        assert not result.too_many_questions

    def test_generic_validation_lowers_score(self):
        text = "Я слышу, что тебе сейчас плохо. Это совершенно нормально чувствовать."
        result = score_talk_humanness(text, "мне плохо")
        assert result.has_generic_validation
        assert result.score < 80

    def test_multiple_questions_penalised(self):
        text = "Как ты себя чувствуешь? Что произошло? Расскажи мне больше?"
        result = score_talk_humanness(text, "мне плохо")
        assert result.too_many_questions
        assert result.question_count == 3
        assert result.score <= 70

    def test_therapy_jargon_penalised(self):
        text = "Давай используем когнитивную технику чтобы справиться с этим."
        result = score_talk_humanness(text, "тревога")
        assert result.has_therapy_jargon
        assert result.score < 80

    def test_markdown_penalised(self):
        text = "**Я слышу тебя.** Это _очень_ тяжело."
        result = score_talk_humanness(text, "тяжело")
        assert result.has_markdown
        assert result.score < 90

    def test_too_long_penalised(self):
        # 6+ sentences
        text = (
            "Это очень тяжело. "
            "Я понимаю. "
            "Это нормально. "
            "Многие через это проходят. "
            "Ты не один. "
            "Что ты сейчас чувствуешь?"
        )
        result = score_talk_humanness(text, "тяжело")
        assert result.too_long
        assert result.score < 85

    def test_no_anchor_penalised(self):
        # Response ignores user's specific words entirely
        text = "Расскажи подробнее."
        result = score_talk_humanness(text, "мой развод с женой после 19 лет брака")
        assert result.lacks_specific_anchor

    def test_anchor_present_not_penalised(self):
        text = "19 лет — это огромная часть жизни. Как ты сейчас?"
        result = score_talk_humanness(text, "мой развод с женой после 19 лет брака")
        assert not result.lacks_specific_anchor

    def test_english_generic_phrases_detected(self):
        text = "I understand how difficult this must be. Your feelings are valid."
        result = score_talk_humanness(text, "divorce after 19 years")
        assert result.has_generic_validation
        assert result.score < 80

    def test_english_therapy_jargon_detected(self):
        text = "Let's use a cognitive reframing technique for emotional regulation."
        result = score_talk_humanness(text, "I feel anxious")
        assert result.has_therapy_jargon

    def test_golden_ru_short_warm(self):
        text = "Расскажи. Что случилось?"
        result = score_talk_humanness(text, "мне плохо")
        assert result.score >= 90
        assert result.question_count == 1
        assert not result.too_many_questions

    def test_golden_divorce_anchor(self):
        text = "19 лет — это не просто отношения, это целая часть жизни. Что сейчас больнее всего?"
        result = score_talk_humanness(text, "мой развод с женой после 19 лет брака")
        assert result.score >= 80
        assert not result.has_generic_validation

    def test_golden_survive_short(self):
        text = "Да. По одному шагу. Ты не один в этом."
        result = score_talk_humanness(text, "пережить его")
        assert result.score >= 85
        assert result.question_count == 0


# ── should_repair_talk_response ───────────────────────────────────────────────


class TestShouldRepair:
    def test_high_score_no_repair(self):
        result = TalkHumanizationResult(score=80)
        assert not should_repair_talk_response(result)

    def test_low_score_triggers_repair(self):
        result = TalkHumanizationResult(score=59)
        assert should_repair_talk_response(result)

    def test_threshold_boundary(self):
        assert should_repair_talk_response(TalkHumanizationResult(score=59))
        assert not should_repair_talk_response(TalkHumanizationResult(score=60))

    def test_mechanical_response_triggers_repair(self):
        text = (
            "Я понимаю, как тебе сейчас тяжело. "
            "Твои чувства важны и понятны. "
            "Это совершенно нормально чувствовать боль после развода. "
            "Что именно тебя беспокоит больше всего?"
        )
        result = score_talk_humanness(text, "развод")
        assert should_repair_talk_response(result)


# ── humanize_talk_response ────────────────────────────────────────────────────


class TestHumanizeTalkResponse:
    def test_strips_markdown(self):
        text = "**Я слышу тебя.** Это _тяжело_."
        cleaned = humanize_talk_response(text, "мне плохо")
        assert "*" not in cleaned
        assert "_" not in cleaned

    def test_preserves_plain_text(self):
        text = "Расскажи подробнее. Что случилось?"
        assert humanize_talk_response(text, "мне плохо") == text

    def test_no_markdown_in_clean_text(self):
        text = "Это правда тяжело. Ты справляешься?"
        result = humanize_talk_response(text, "тяжело")
        assert "#" not in result
        assert "`" not in result


# ── Golden dialogue constraints ───────────────────────────────────────────────


class TestGoldenDialogue:
    """Structural checks for golden Talk Mode scenarios (no LLM — constraints only)."""

    _GOLDEN_PAIRS = [
        ("мне плохо", "Расскажи. Что случилось?"),
        ("мой развод с женой после 19 лет брака",
         "19 лет — это не просто отношения, это целая часть жизни. Что сейчас больнее всего?"),
        ("пережить его...", "Да. По одному шагу. Ты не один в этом."),
        ("I broke up with someone and it hurts badly.",
         "That kind of pain is real. What hurts most right now?"),
        ("I feel empty after the divorce.",
         "Empty makes sense. Nineteen years leaves a big space. What's the hardest part of the day?"),
    ]

    @pytest.mark.parametrize("user_msg,response", _GOLDEN_PAIRS)
    def test_no_markdown(self, user_msg, response):
        assert "*" not in response
        assert "#" not in response
        assert "`" not in response

    @pytest.mark.parametrize("user_msg,response", _GOLDEN_PAIRS)
    def test_at_most_one_question(self, user_msg, response):
        assert response.count("?") <= 1

    @pytest.mark.parametrize("user_msg,response", _GOLDEN_PAIRS)
    def test_not_too_long(self, user_msg, response):
        import re
        sentence_count = len(re.findall(r"[.!?…]+", response))
        assert sentence_count <= 5, f"Too long ({sentence_count} sentences): {response}"

    @pytest.mark.parametrize("user_msg,response", _GOLDEN_PAIRS)
    def test_no_generic_validation(self, user_msg, response):
        result = score_talk_humanness(response, user_msg)
        assert not result.has_generic_validation, f"Generic phrase in: {response}"

    @pytest.mark.parametrize("user_msg,response", _GOLDEN_PAIRS)
    def test_no_therapy_jargon(self, user_msg, response):
        result = score_talk_humanness(response, user_msg)
        assert not result.has_therapy_jargon, f"Therapy jargon in: {response}"
