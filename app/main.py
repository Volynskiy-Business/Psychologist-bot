"""Application entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.bot.handlers import chat, exercises, mood, start
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(exercises.router)
    dp.include_router(mood.router)
    dp.include_router(chat.router)
    return dp


async def main() -> None:
    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = create_dispatcher()

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню / Main menu"),
    ])

    logger.info("Starting %s", settings.bot_display_name)
    logger.info(
        "config: default_model=%s classifier_model=%s",
        settings.default_model,
        settings.classifier_model or "(fallback to default_model)",
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
