"""Keyboards for timezone selection."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Common timezones for manual selection
COMMON_TIMEZONES = [
    "Europe/Moscow",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Cyprus",
    "Asia/Dubai",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "Australia/Sydney",
]


def get_location_request_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard to request location from user."""
    keyboard = [
        [KeyboardButton(text="📍 Поделиться местоположением", request_location=True)],
        [KeyboardButton(text="⌚ Выбрать часовой пояс вручную")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_timezone_selection_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with common timezones."""
    buttons = []
    for tz in COMMON_TIMEZONES:
        # Extract readable name (e.g., "Europe/Moscow" -> "Moscow")
        display_name = tz.split("/")[-1].replace("_", " ")
        buttons.append([InlineKeyboardButton(text=f"🌍 {display_name}", callback_data=f"tz:{tz}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_settings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to manage reminder settings."""
    buttons = [
        [
            InlineKeyboardButton(
                text="⏰ Настроить напоминания о еде",
                callback_data="set_food_reminders",
            )
        ],
        [
            InlineKeyboardButton(
                text="💊 Настроить напоминания о симптомах",
                callback_data="set_symptom_reminders",
            )
        ],
        [InlineKeyboardButton(text="✅ Готово", callback_data="finish_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
