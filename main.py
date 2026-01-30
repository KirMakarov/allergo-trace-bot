"""Main entry point for the Allergo Trace Bot."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from allergo_trace_bot.config import settings
from allergo_trace_bot.database.core import async_engine, init_db
from allergo_trace_bot.handlers import dish_router, food_log_router, food_router
from allergo_trace_bot.middlewares import RegistrationMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """Initialize database on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")


async def main() -> None:
    """Run the bot."""
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Create session factory
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Middleware to inject session into handlers
    async def session_middleware(
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_factory() as session:
            data["session"] = session
            return await handler(event, data)

    # Register middlewares
    dp.update.outer_middleware(session_middleware)
    dp.update.middleware(RegistrationMiddleware())

    # Register routers (order matters - more specific routers first!)
    dp.include_router(dish_router)  # Dish creation has priority
    dp.include_router(food_log_router)  # Food logging second
    dp.include_router(food_router)  # General food operations last

    # Startup actions
    await on_startup()

    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
