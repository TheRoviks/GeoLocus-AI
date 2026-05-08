import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import build_root_router
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from core.config import get_settings
from core.logger import configure_logging, get_logger
from db.session import get_session_factory
from services.ai_service import AIService
from services.scheduler_service import SchedulerService


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, debug=settings.debug)
    log = get_logger("bot.main")

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    session_factory = get_session_factory()
    ai = AIService(settings)
    scheduler = SchedulerService(bot, session_factory)

    dp = Dispatcher()
    dp["ai"] = ai
    dp["scheduler"] = scheduler

    dp.message.middleware(ThrottlingMiddleware(rate_per_second=1.0))
    dp.message.middleware(AuthMiddleware(session_factory, settings.default_timezone))
    dp.callback_query.middleware(AuthMiddleware(session_factory, settings.default_timezone))

    dp.include_router(build_root_router())

    await scheduler.start()
    log.info("bot_starting")

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        await scheduler.shutdown()
        await ai.aclose()
        await bot.session.close()
        log.info("bot_stopped")


if __name__ == "__main__":
    asyncio.run(main())
