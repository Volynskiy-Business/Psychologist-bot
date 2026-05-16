"""Safety protocols and crisis responses."""

from app.db.models import RiskLevel


CRISIS_RESPONSE_TEMPLATE = """Похоже, сейчас может быть небезопасный момент. Я не могу заменить живую помощь — сейчас важнее всего связаться с реальным человеком.

Пожалуйста, позвони в местную экстренную службу или на местную кризисную линию прямо сейчас. Если можешь — напиши или позови кого-то близкого рядом и скажи, что тебе нужна поддержка.

Отложи подальше всё, чем можно причинить себе вред.

Ты сейчас один/одна?"""

ELEVATED_DISTRESS_RESPONSE = """Я слышу, что тебе очень тяжело. Это важно и серьёзно.

Я могу помочь с маленькими шагами прямо сейчас, но если тебе плохо уже долго или становится хуже, пожалуйста, обратись к специалисту.

Хочешь, сделаем одно короткое упражнение для стабилизации?"""


def get_crisis_response(risk_level: RiskLevel, lang: str = "en") -> str:
    """Get crisis response in user's language."""
    from app.bot.handlers.i18n import get_text

    if risk_level == RiskLevel.IMMINENT_RISK:
        return get_text("crisis.response", lang)
    elif risk_level == RiskLevel.POSSIBLE_CRISIS:
        return get_text("crisis.elevated", lang)
    elif risk_level == RiskLevel.ELEVATED_DISTRESS:
        return get_text("crisis.passive_risk", lang)
    return ""


def get_safety_plan_template(lang: str = "en") -> str:
    """Get safety plan template in user's language."""
    from app.bot.handlers.i18n import get_text

    title = get_text("safety_plan.title", lang)
    items = get_text("safety_plan.items", lang)
    start = get_text("safety_plan.start_filling", lang)

    if isinstance(items, list):
        items_text = "\n".join(items)
    else:
        items_text = str(items)

    return f"{title}\n\n{items_text}\n\n{start}"
