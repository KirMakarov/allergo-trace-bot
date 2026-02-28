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
                KeyboardButton(text="🍽 Записать еду"),
                KeyboardButton(text="📋 Мои блюда"),
            ],
            [
                KeyboardButton(text="🥗 Добавить продукт"),
                KeyboardButton(text="🍳 Новое блюдо"),
            ],
            [
                KeyboardButton(text="📊 Анализ"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
            [
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие или введите команду...",
    )
    return keyboard


# Mapping from button text to command
BUTTON_TO_COMMAND: dict[str, str] = {
    "🍽 Записать еду": "/log_food",
    "📋 Мои блюда": "/my_dishes",
    "🥗 Добавить продукт": "/food",
    "🍳 Новое блюдо": "/new_dish",
    "📊 Анализ": "/analyze",
    "⚙️ Настройки": "/settings",
    "❓ Помощь": "/help",
}
