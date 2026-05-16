"""Mood diary handler — summary card, history, notes, and trend views."""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, types
from aiogram.filters import Command

from app.bot.handlers.i18n import get_text, get_user_language
from app.db.models import MoodEntry
from app.services.user_service import (
    get_mood_history,
    get_mood_trend_data,
    save_mood_entry,
)

logger = logging.getLogger(__name__)
router = Router()

# In-memory set of user IDs that clicked "Add a note" and haven't typed yet.
# Lost on restart — degrades to normal chat flow, which is acceptable.
_awaiting_note: set[int] = set()


def is_awaiting_note(user_id: int) -> bool:
    return user_id in _awaiting_note


def consume_note_waiter(user_id: int) -> None:
    _awaiting_note.discard(user_id)


# ── Mood score helpers ────────────────────────────────────────────────────────


def _mood_bar(score: int) -> str:
    total = 12
    filled = max(0, min(total, round(score / 5 * total)))
    return "🟧" * filled + "⬜" * (total - filled)


def _compute_trend(scores: list[int]) -> str:
    """Return trend key from a descending-ordered score list (most recent first)."""
    n = len(scores)
    if n < 3:
        return "stable"
    mid = n // 2
    # scores[0] is most recent; older entries are at the end
    newer_avg = sum(scores[:mid]) / mid
    older_avg = sum(scores[mid:]) / (n - mid)
    diff = newer_avg - older_avg
    if diff > 0.5:
        return "improving"
    if diff < -0.5:
        return "declining"
    return "mixed" if (max(scores) - min(scores)) >= 2 else "stable"


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _format_entry_date(entry_dt: datetime, lang: str) -> str:
    months_en = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    months_ru = [
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек",
    ]
    months = months_ru if lang == "ru" else months_en
    return f"{entry_dt.day} {months[entry_dt.month - 1]}"


# ── Summary card builder ──────────────────────────────────────────────────────


def _build_summary_text(history: list[MoodEntry], current_score: int, lang: str) -> str:
    title = get_text("mood.summary.title", lang)
    label = get_text(f"mood.levels.{current_score}", lang)
    bar = _mood_bar(current_score)

    cutoff = _utc_now_naive() - timedelta(days=7)
    week_entries = [e for e in history if e.created_at >= cutoff]
    count = len(week_entries)

    count_line = (
        get_text("mood.summary.week_count_one", lang)
        if count <= 1
        else get_text("mood.summary.week_count", lang, count=count)
    )

    scores = [e.mood_score for e in history if e.mood_score is not None]
    trend_text = ""
    if len(scores) >= 3:
        trend_key = _compute_trend(scores)
        trend_label = get_text("mood.summary.trend_label", lang)
        trend_val = get_text(f"mood.summary.trend_{trend_key}", lang)
        trend_text = f"\n{trend_label}: {trend_val}"

    return f"{title}\n\n{label}\n{bar}  {current_score}/5\n\n{count_line}{trend_text}"


def _summary_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.buttons.add_note", lang),
                    callback_data="add_mood_note",
                ),
                types.InlineKeyboardButton(
                    text=get_text("mood.buttons.history", lang),
                    callback_data="mood_history",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.buttons.notes", lang),
                    callback_data="mood_notes",
                ),
                types.InlineKeyboardButton(
                    text=get_text("mood.buttons.trend", lang),
                    callback_data="mood_trend",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("menu.back_to_menu", lang),
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


async def send_mood_summary(message: types.Message, user_id: int, lang: str) -> None:
    """Show Mood Summary Card via message.answer() — called from chat.py after note save."""
    history = await get_mood_history(user_id, limit=7)
    if not history:
        await message.answer(
            get_text("mood.summary.title", lang), reply_markup=_summary_keyboard(lang)
        )
        return
    card = _build_summary_text(history, history[0].mood_score, lang)
    await message.answer(card, reply_markup=_summary_keyboard(lang))


# ── /mood command ─────────────────────────────────────────────────────────────


@router.message(Command("mood"))
async def cmd_mood(message: types.Message) -> None:
    lang = get_user_language(message.from_user)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.5", lang), callback_data="mood_5"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.4", lang), callback_data="mood_4"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.3", lang), callback_data="mood_3"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.2", lang), callback_data="mood_2"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=get_text("mood.levels.1", lang), callback_data="mood_1"
                )
            ],
        ]
    )
    await message.answer(get_text("mood.question", lang), reply_markup=keyboard)


# ── Mood selection callback ───────────────────────────────────────────────────


@router.callback_query(lambda c: c.data.startswith("mood_") and c.data[5:].isdigit())
async def on_mood_selected(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    mood = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    try:
        await save_mood_entry(user_id, mood)
        history = await get_mood_history(user_id, limit=7)
        card = _build_summary_text(history, mood, lang)
        await callback.message.edit_text(card, reply_markup=_summary_keyboard(lang))
    except Exception:
        logger.exception("Failed to save mood entry for user <REDACTED>")
        await callback.message.edit_text(
            get_text("chat.error", lang),
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text=get_text("menu.back_to_menu", lang),
                            callback_data="back_to_menu",
                        )
                    ]
                ]
            ),
        )
    await callback.answer()


# ── Add note callback ─────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "add_mood_note")
async def on_mood_add_note(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    _awaiting_note.add(callback.from_user.id)
    await callback.message.edit_text(
        get_text("mood.add_note_prompt", lang),
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ── History view ──────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "mood_history")
async def on_mood_history(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user_id = callback.from_user.id
    history = await get_mood_history(user_id, limit=7)

    title = get_text("mood.history.title", lang)
    if not history:
        text = f"{title}\n\n{get_text('mood.history.empty', lang)}"
    else:
        header = get_text("mood.history.header", lang, count=len(history))
        lines = [f"{title}\n\n{header}\n"]
        for entry in history:
            date_str = _format_entry_date(entry.created_at, lang)
            mood_label = get_text(f"mood.levels.{entry.mood_score}", lang)
            lines.append(f"{date_str} · {mood_label} · {entry.mood_score}/5")
            if entry.notes:
                preview = entry.notes[:80] + ("…" if len(entry.notes) > 80 else "")
                lines.append(f'  "{preview}"')
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ── Notes view ────────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "mood_notes")
async def on_mood_notes(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user_id = callback.from_user.id
    history = await get_mood_history(user_id, limit=14)
    with_notes = [e for e in history if e.notes]

    title = get_text("mood.notes.title", lang)
    if not with_notes:
        text = f"{title}\n\n{get_text('mood.notes.empty', lang)}"
    else:
        header = get_text("mood.notes.header", lang)
        lines = [f"{title}\n\n{header}\n"]
        for entry in with_notes[:7]:
            date_str = _format_entry_date(entry.created_at, lang)
            preview = entry.notes[:120] + ("…" if len(entry.notes) > 120 else "")
            lines.append(f'{date_str} — "{preview}"')
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]
            ]
        ),
    )
    await callback.answer()


# ── Trend view ────────────────────────────────────────────────────────────────


@router.callback_query(lambda c: c.data == "mood_trend")
async def on_mood_trend(callback: types.CallbackQuery) -> None:
    lang = get_user_language(callback.from_user)
    user_id = callback.from_user.id
    data = await get_mood_trend_data(user_id, days=7)

    title = get_text("mood.trend.title", lang)
    count = data.get("count", 0)

    if count < 3:
        text = f"{title}\n\n{get_text('mood.trend.need_more', lang, count=count)}"
    else:
        avg = data["avg"]
        high = data["high"]
        low = data["low"]
        scores = [e.mood_score for e in data["entries"] if e.mood_score is not None]
        trend_key = _compute_trend(scores)
        insight = get_text(f"mood.trend.insight_{trend_key}", lang)
        text = (
            f"{title}\n\n"
            f"{get_text('mood.trend.average', lang, avg=avg)}\n"
            f"{get_text('mood.trend.high', lang, high=high)}\n"
            f"{get_text('mood.trend.low', lang, low=low)}\n\n"
            f"{insight}"
        )

    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=get_text("menu.back_to_menu", lang),
                        callback_data="back_to_menu",
                    )
                ]
            ]
        ),
    )
    await callback.answer()
