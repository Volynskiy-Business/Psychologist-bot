"""Application entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.bot.handlers import chat, exercises, mood, safety_plan, start
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


_BOT_COMMANDS = [
    BotCommand(command="start", description="Main menu / Главное меню"),
    BotCommand(command="chat", description="Chat / Поговорить"),
    BotCommand(command="mood", description="Mood diary / Дневник настроения"),
]


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(exercises.router)
    dp.include_router(mood.router)
    dp.include_router(safety_plan.router)
    dp.include_router(chat.router)
    return dp


async def main() -> None:
    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = create_dispatcher()

    await bot.set_my_commands(_BOT_COMMANDS)
    logger.info("Telegram bot commands registered")

    logger.info("Starting %s", settings.bot_display_name)
    logger.info(
        "config: default_model=%s classifier_model=%s",
        settings.default_model,
        settings.classifier_model or "(disabled)",
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
