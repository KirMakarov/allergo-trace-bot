"""Handlers for timezone and reminder settings."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    Message,
    ReplyKeyboardRemove,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from timezonefinder import TimezoneFinder

from allergo_trace_bot.database.models.user import User
from allergo_trace_bot.keyboards.timezone import (
    get_location_request_keyboard,
    get_reminder_settings_keyboard,
    get_timezone_selection_keyboard,
)
from allergo_trace_bot.utils.datetime_utils import get_current_user_time

logger = logging.getLogger(__name__)
router = Router(name="timezone_router")
tf = TimezoneFinder()


class ReminderStates(StatesGroup):
    """States for reminder configuration."""

    waiting_for_food_reminders = State()  # Waiting for food reminder times
    waiting_for_symptom_reminders = State()  # Waiting for symptom reminder times


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession, db_user: User) -> None:
    """Handle /settings command to configure timezone and reminders."""
    if not message.from_user:
        return

    # Check if user already has timezone configured
    if db_user.timezone != "UTC":
        # User has timezone, show current settings
        user_time = get_current_user_time(db_user.timezone)
        food_times = ", ".join(db_user.settings.get("food_reminders", [])) or "не настроены"
        symptom_times = ", ".join(db_user.settings.get("symptom_reminders", [])) or "не настроены"

        await message.answer(
            f"⚙️ <b>Ваши настройки</b>\n\n"
            f"🌍 <b>Часовой пояс:</b> {db_user.timezone}\n"
            f"🕐 <b>Текущее время:</b> {user_time.strftime('%H:%M')}\n\n"
            f"🍽 <b>Напоминания о еде:</b> {food_times}\n"
            f"💊 <b>Напоминания о симптомах:</b> {symptom_times}\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=get_reminder_settings_keyboard(show_change_timezone=True),
        )
    else:
        # New user, show timezone setup
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
        user_time = get_current_user_time(timezone_str)
        await message.answer(
            f"✅ <b>Часовой пояс установлен:</b> {timezone_str}\n"
            f"🕐 <b>Ваше текущее время:</b> {user_time.strftime('%H:%M')}\n\n"
            "Теперь настройте напоминания:",
            reply_markup=get_reminder_settings_keyboard(show_change_timezone=True),
        )
        # Remove the location request keyboard
        await message.answer(
            "⚙️ Используйте кнопки выше для настройки напоминаний.",
            reply_markup=ReplyKeyboardRemove(),
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
    # Remove reply keyboard
    await message.answer(
        "⌚ Используйте кнопки выше для выбора часового пояса.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(F.data.startswith("tz:"))
async def handle_timezone_selection(callback: CallbackQuery, session: AsyncSession) -> None:
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
        user_time = get_current_user_time(timezone_str)

        # Type narrowing for callback.message
        if not callback.message or isinstance(callback.message, InaccessibleMessage):
            await callback.answer("Message is not accessible")
            return

        await callback.message.edit_text(
            f"✅ <b>Часовой пояс установлен:</b> {timezone_str}\n"
            f"🕐 <b>Ваше текущее время:</b> {user_time.strftime('%H:%M')}\n\n"
            "Теперь настройте напоминания:",
            reply_markup=get_reminder_settings_keyboard(show_change_timezone=True),
        )
        await callback.answer()

        # Send a new message to remove the reply keyboard
        if callback.bot:
            await callback.bot.send_message(
                chat_id=callback.from_user.id,
                text="⚙️ Используйте кнопки выше для настройки напоминаний.",
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        await callback.answer("❌ Ошибка: пользователь не найден.", show_alert=True)


@router.callback_query(F.data == "set_food_reminders")
async def set_food_reminders(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    """Start setting food reminders."""
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return

    current_times = ", ".join(db_user.settings.get("food_reminders", [])) or "не настроены"

    await state.set_state(ReminderStates.waiting_for_food_reminders)
    await callback.message.edit_text(
        f"⏰ <b>Напоминания о еде</b>\n\n"
        f"Текущие: {current_times}\n\n"
        f"Введите новые времена в формате HH:MM, разделённые запятой.\n"
        f"Например: <code>09:00, 14:00, 20:00</code>\n\n"
        f"• Можно указать от 0 до 10 напоминаний\n"
        f"• Чтобы отключить напоминания, отправьте: <code>нет</code>\n"
        f"• Для отмены используйте /stop",
        reply_markup=None,
    )
    await callback.answer()


@router.message(StateFilter(ReminderStates.waiting_for_food_reminders))
async def process_food_reminders(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process food reminder times input."""
    if not message.text:
        return

    text = message.text.strip().lower()

    # Check if user wants to disable reminders
    if text in ["нет", "no", "отключить", "disable", "0"]:
        db_user.settings["food_reminders"] = []
        flag_modified(db_user, "settings")
        await session.commit()
        await state.clear()
        await message.answer(
            "✅ Напоминания о еде отключены.\n\nИспользуйте /settings для изменения.",
        )
        return

    # Parse times
    times_raw = [t.strip() for t in message.text.split(",")]
    times = []
    errors = []

    for time_str in times_raw:
        if not time_str:
            continue
        try:
            # Validate HH:MM format
            parts = time_str.split(":")
            if len(parts) != 2:
                errors.append(f"'{time_str}' - неверный формат")
                continue

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                errors.append(f"'{time_str}' - время вне диапазона")
                continue

            # Format as HH:MM
            formatted_time = f"{hour:02d}:{minute:02d}"
            if formatted_time not in times:
                times.append(formatted_time)
        except ValueError:
            errors.append(f"'{time_str}' - неверный формат")

    # Validate count
    if len(times) > 10:
        await message.answer("❌ Слишком много напоминаний!\n\nМаксимум 10 напоминаний в сутки.\nПопробуйте еще раз.")
        return

    if errors:
        await message.answer(
            "⚠️ <b>Ошибки в некоторых значениях:</b>\n"
            + "\n".join(f"• {e}" for e in errors)
            + "\n\nПопробуйте еще раз или используйте /stop для отмены."
        )
        return

    if not times:
        await message.answer(
            "❌ Не указано ни одного корректного времени.\n\n"
            "Попробуйте еще раз или отправьте <code>нет</code> для отключения напоминаний."
        )
        return

    # Sort times
    times.sort()

    # Save to database
    db_user.settings["food_reminders"] = times
    flag_modified(db_user, "settings")
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Напоминания о еде сохранены!</b>\n\nВремя: {', '.join(times)}\n\nИспользуйте /settings для изменения."
    )


@router.callback_query(F.data == "set_symptom_reminders")
async def set_symptom_reminders(callback: CallbackQuery, state: FSMContext, db_user: User) -> None:
    """Start setting symptom reminders."""
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return

    current_times = ", ".join(db_user.settings.get("symptom_reminders", [])) or "не настроены"

    await state.set_state(ReminderStates.waiting_for_symptom_reminders)
    await callback.message.edit_text(
        f"💊 <b>Напоминания о симптомах</b>\n\n"
        f"Текущие: {current_times}\n\n"
        f"Введите новые времена в формате HH:MM, разделённые запятой.\n"
        f"Например: <code>09:00, 21:00</code>\n\n"
        f"• Можно указать от 0 до 10 напоминаний\n"
        f"• Чтобы отключить напоминания, отправьте: <code>нет</code>\n"
        f"• Для отмены используйте /stop",
        reply_markup=None,
    )
    await callback.answer()


@router.message(StateFilter(ReminderStates.waiting_for_symptom_reminders))
async def process_symptom_reminders(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process symptom reminder times input."""
    if not message.text:
        return

    text = message.text.strip().lower()

    # Check if user wants to disable reminders
    if text in ["нет", "no", "отключить", "disable", "0"]:
        db_user.settings["symptom_reminders"] = []
        flag_modified(db_user, "settings")
        await session.commit()
        await state.clear()
        await message.answer(
            "✅ Напоминания о симптомах отключены.\n\nИспользуйте /settings для изменения.",
        )
        return

    # Parse times
    times_raw = [t.strip() for t in message.text.split(",")]
    times = []
    errors = []

    for time_str in times_raw:
        if not time_str:
            continue
        try:
            # Validate HH:MM format
            parts = time_str.split(":")
            if len(parts) != 2:
                errors.append(f"'{time_str}' - неверный формат")
                continue

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                errors.append(f"'{time_str}' - время вне диапазона")
                continue

            # Format as HH:MM
            formatted_time = f"{hour:02d}:{minute:02d}"
            if formatted_time not in times:
                times.append(formatted_time)
        except ValueError:
            errors.append(f"'{time_str}' - неверный формат")

    # Validate count
    if len(times) > 10:
        await message.answer("❌ Слишком много напоминаний!\n\nМаксимум 10 напоминаний в сутки.\nПопробуйте еще раз.")
        return

    if errors:
        await message.answer(
            "⚠️ <b>Ошибки в некоторых значениях:</b>\n"
            + "\n".join(f"• {e}" for e in errors)
            + "\n\nПопробуйте еще раз или используйте /stop для отмены."
        )
        return

    if not times:
        await message.answer(
            "❌ Не указано ни одного корректного времени.\n\n"
            "Попробуйте еще раз или отправьте <code>нет</code> для отключения напоминаний."
        )
        return

    # Sort times
    times.sort()

    # Save to database
    db_user.settings["symptom_reminders"] = times
    flag_modified(db_user, "settings")
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Напоминания о симптомах сохранены!</b>\n\n"
        f"Время: {', '.join(times)}\n\n"
        f"Используйте /settings для изменения."
    )


@router.callback_query(F.data == "change_timezone")
async def change_timezone(callback: CallbackQuery) -> None:
    """Show timezone selection when user wants to change it."""
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return

    await callback.message.edit_text(
        "🌍 <b>Выберите новый часовой пояс:</b>",
        reply_markup=get_timezone_selection_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "finish_settings")
async def finish_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    """Finish settings configuration."""
    if not callback.from_user or not callback.message:
        return

    # Type narrowing for callback.message
    if isinstance(callback.message, InaccessibleMessage):
        await callback.answer("Message is not accessible")
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
            f"Используйте /settings чтобы изменить настройки.",
            reply_markup=None,
        )
    await callback.answer()
