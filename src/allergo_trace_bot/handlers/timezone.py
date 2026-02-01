"""Handlers for timezone and reminder settings."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from timezonefinder import TimezoneFinder

from allergo_trace_bot.database.models.user import User
from allergo_trace_bot.keyboards.timezone import (
    get_location_request_keyboard,
    get_reminder_settings_keyboard,
    get_timezone_selection_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="timezone_router")
tf = TimezoneFinder()


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    """Handle /settings command to configure timezone and reminders."""
    await message.answer(
        "⚙️ <b>Настройка напоминаний</b>\n\n"
        "Для точных напоминаний мне нужно знать ваш часовой пояс.\n"
        "Вы можете поделиться местоположением или выбрать вручную:",
        reply_markup=get_location_request_keyboard(),
    )


@router.message(F.location)
async def handle_location(message: Message, session: AsyncSession) -> None:
    """Handle location sharing to determine timezone."""
    if not message.location or not message.from_user:
        return

    latitude = message.location.latitude
    longitude = message.location.longitude

    # Get timezone from coordinates
    timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

    if not timezone_str:
        await message.answer(
            "❌ Не удалось определить часовой пояс по вашему местоположению.\n"
            "Пожалуйста, выберите часовой пояс вручную:",
            reply_markup=get_timezone_selection_keyboard(),
        )
        return

    # Update user timezone
    result = await session.execute(select(User).where(User.id == message.from_user.id))
    user = result.scalar_one_or_none()

    if user:
        user.timezone = timezone_str
        await session.commit()

        # Show current time in user's timezone
        user_time = datetime.now(ZoneInfo(timezone_str))
        await message.answer(
            f"✅ <b>Часовой пояс установлен:</b> {timezone_str}\n"
            f"🕐 <b>Ваше текущее время:</b> {user_time.strftime('%H:%M')}\n\n"
            "Теперь настройте напоминания:",
            reply_markup=get_reminder_settings_keyboard(),
        )
    else:
        await message.answer("❌ Ошибка: пользователь не найден.")


@router.message(F.text == "⌚ Выбрать часовой пояс вручную")
async def manual_timezone_selection(message: Message) -> None:
    """Show manual timezone selection keyboard."""
    await message.answer(
        "🌍 <b>Выберите ваш часовой пояс:</b>",
        reply_markup=get_timezone_selection_keyboard(),
    )


@router.callback_query(F.data.startswith("tz:"))
async def handle_timezone_selection(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Handle timezone selection from inline keyboard."""
    if not callback.data or not callback.from_user or not callback.message:
        return

    timezone_str = callback.data.split(":", 1)[1]

    # Update user timezone
    result = await session.execute(select(User).where(User.id == callback.from_user.id))
    user = result.scalar_one_or_none()

    if user:
        user.timezone = timezone_str
        await session.commit()

        # Show current time in user's timezone
        user_time = datetime.now(ZoneInfo(timezone_str))
        await callback.message.edit_text(
            f"✅ <b>Часовой пояс установлен:</b> {timezone_str}\n"
            f"🕐 <b>Ваше текущее время:</b> {user_time.strftime('%H:%M')}\n\n"
            "Теперь настройте напоминания:",
            reply_markup=get_reminder_settings_keyboard(),
        )
    else:
        await callback.answer("❌ Ошибка: пользователь не найден.", show_alert=True)


@router.callback_query(F.data == "set_food_reminders")
async def set_food_reminders(callback: CallbackQuery) -> None:
    """Placeholder for setting food reminders."""
    await callback.answer(
        "Отправьте время напоминаний о еде в формате HH:MM, разделенные запятой\n"
        "Например: 09:00, 14:00, 20:00",
        show_alert=True,
    )
    # TODO: Implement FSM state to capture reminder times


@router.callback_query(F.data == "set_symptom_reminders")
async def set_symptom_reminders(callback: CallbackQuery) -> None:
    """Placeholder for setting symptom reminders."""
    await callback.answer(
        "Отправьте время напоминаний о симптомах в формате HH:MM, разделенные запятой\n"
        "Например: 09:00, 21:00",
        show_alert=True,
    )
    # TODO: Implement FSM state to capture reminder times


@router.callback_query(F.data == "finish_settings")
async def finish_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    """Finish settings configuration."""
    if not callback.from_user or not callback.message:
        return

    result = await session.execute(select(User).where(User.id == callback.from_user.id))
    user = result.scalar_one_or_none()

    if user:
        food_times = ", ".join(user.settings.get("food_reminders", []))
        symptom_times = ", ".join(user.settings.get("symptom_reminders", []))

        await callback.message.edit_text(
            f"✅ <b>Настройки сохранены!</b>\n\n"
            f"🌍 <b>Часовой пояс:</b> {user.timezone}\n"
            f"🍽 <b>Напоминания о еде:</b> {food_times}\n"
            f"💊 <b>Напоминания о симптомах:</b> {symptom_times}\n\n"
            f"Используйте /settings чтобы изменить настройки."
        )
    await callback.answer()
