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
        [KeyboardButton(text="📍 Share Location", request_location=True)],
        [KeyboardButton(text="⌚ Select Timezone Manually")],
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


def get_reminder_settings_keyboard(
    show_change_timezone: bool = False,
) -> InlineKeyboardMarkup:
    """Keyboard to manage reminder settings.

    Args:
        show_change_timezone: Whether to show button to change timezone
    """
    buttons = []

    if show_change_timezone:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🌍 Change Timezone",
                    callback_data="change_timezone",
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="⏰ Configure Food Reminders",
                    callback_data="set_food_reminders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💊 Configure Symptom Reminders",
                    callback_data="set_symptom_reminders",
                )
            ],
            [InlineKeyboardButton(text="✅ Done", callback_data="finish_settings")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
