"""Scheduler for sending reminders to users."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from allergo_trace_bot.database.models.user import User

logger = logging.getLogger(__name__)


async def check_reminders(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """
    Check if any users need to receive reminders at the current time.

    This function runs every minute and:
    1. Queries all active users with reminder settings
    2. Checks current time in each user's timezone
    3. Sends reminder if current time matches any reminder time

    Args:
        bot: Aiogram Bot instance to send messages
        session_factory: SQLAlchemy async session factory
    """
    async with session_factory() as session:
        # Get all active users with settings
        result = await session.execute(select(User).where(User.is_active == True))  # noqa: E712
        users = result.scalars().all()

        for user in users:
            try:
                # Get current time in user's timezone
                user_tz = ZoneInfo(user.timezone)
                now_user = datetime.now(user_tz)
                current_time = now_user.strftime("%H:%M")

                # Check food reminders
                food_reminders = user.settings.get("food_reminders", [])
                if current_time in food_reminders:
                    await send_food_reminder(bot, user.id)
                    logger.info(f"Sent food reminder to user {user.id} at {current_time} ({user.timezone})")

                # Check symptom reminders
                symptom_reminders = user.settings.get("symptom_reminders", [])
                if current_time in symptom_reminders:
                    await send_symptom_reminder(bot, user.id)
                    logger.info(f"Sent symptom reminder to user {user.id} at {current_time} ({user.timezone})")

            except Exception as e:
                logger.error(f"Error processing reminders for user {user.id}: {e}")


async def send_food_reminder(bot: Bot, user_id: int) -> None:
    """
    Send food logging reminder to user.

    Args:
        bot: Aiogram Bot instance
        user_id: Telegram user ID
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🍽 <b>Время записать еду!</b>\n\n"
                "Что вы ели сегодня? Используйте:\n"
                "• /log_food - Записать приём пищи\n"
                "• /new_dish - Создать новое блюдо"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to send food reminder to user {user_id}: {e}")


async def send_symptom_reminder(bot: Bot, user_id: int) -> None:
    """
    Send symptom logging reminder to user.

    Args:
        bot: Aiogram Bot instance
        user_id: Telegram user ID
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "💊 <b>Время записать симптомы!</b>\n\n"
                "Как вы себя чувствуете? Есть ли какие-то симптомы?\n"
                "Используйте /symptom для записи."
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to send symptom reminder to user {user_id}: {e}")
