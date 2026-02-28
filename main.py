"""Main entry point for the Allergo Trace Bot."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, TelegramObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from allergo_trace_bot.config import settings
from allergo_trace_bot.database.core import async_engine, init_db
from allergo_trace_bot.handlers import (
    analytics_router,
    dish_router,
    food_log_router,
    food_router,
    menu_buttons_router,
    menu_router,
    set_bot_commands,
    timezone_router,
)
from allergo_trace_bot.keyboards.menu import get_main_menu_keyboard
from allergo_trace_bot.middlewares import (
    AccessControlMiddleware,
    RegistrationMiddleware,
)
from allergo_trace_bot.scheduler import check_reminders

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Initialize database and set bot commands on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    # Set bot commands menu
    logger.info("Setting bot commands menu...")
    await set_bot_commands(bot)
    logger.info("Bot commands menu set successfully")


async def main() -> None:
    """Run the bot."""
    # Initialize bot and dispatche
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

    dp.update.outer_middleware(session_middleware)
    dp.update.middleware(RegistrationMiddleware())
    dp.update.middleware(AccessControlMiddleware())

    # Global commands (work in any state)
    @dp.message(Command("stop"))
    async def cmd_stop(message: Message, state: FSMContext) -> None:
        """Universal stop command - cancel any current operation."""
        current_state = await state.get_state()
        await state.clear()

        if current_state:
            await message.answer(
                "✅ <b>Operation cancelled</b>\n\n"
                "You can start a new operation using the buttons below "
                "or commands from the menu.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer(
                "ℹ️ No active operations.\n\nUse the buttons below or commands from the menu.",
                reply_markup=get_main_menu_keyboard(),
            )

    # Register routers (order matters - more specific routers first!)
    dp.include_router(dish_router)  # Dish creation has priority
    dp.include_router(food_log_router)  # Food logging second
    dp.include_router(food_router)  # General food operations
    dp.include_router(timezone_router)  # Timezone and settings
    dp.include_router(analytics_router)  # Analytics
    dp.include_router(menu_buttons_router)  # Menu button handlers
    dp.include_router(menu_router)  # Menu and help commands

    # Setup scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_reminders,
        trigger="interval",
        minutes=1,
        args=[bot, session_factory],
        id="check_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started - checking reminders every minute")

    # Startup actions
    await on_startup(bot)

    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
        await bot.session.close()
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
