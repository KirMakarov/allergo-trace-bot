"""Reply keyboard for main menu."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Build the main menu reply keyboard.

    This keyboard is always visible below the text input field,
    making frequently used actions accessible with one tap.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🍽 Log Food"),
                KeyboardButton(text="📋 My Dishes"),
            ],
            [
                KeyboardButton(text="🥗 Add Product"),
                KeyboardButton(text="🍳 New Dish"),
            ],
            [
                KeyboardButton(text="📊 Analysis"),
                KeyboardButton(text="⚙️ Settings"),
            ],
            [
                KeyboardButton(text="❓ Help"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Select an action or enter a command...",
    )
    return keyboard


# Mapping from button text to command
BUTTON_TO_COMMAND: dict[str, str] = {
    "🍽 Log Food": "/log_food",
    "📋 My Dishes": "/my_dishes",
    "🥗 Add Product": "/food",
    "🍳 New Dish": "/new_dish",
    "📊 Analysis": "/analyze",
    "⚙️ Settings": "/settings",
    "❓ Help": "/help",
}
