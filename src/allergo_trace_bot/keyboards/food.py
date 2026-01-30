"""Keyboards for food-related interactions."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from allergo_trace_bot.database.models import Ingredient

# Main food categories
FOOD_CATEGORIES = [
    "Овощи",
    "Фрукты",
    "Молочные продукты",
    "Мясо и рыба",
    "Крупы и злаки",
    "Напитки",
    "Сладости",
    "Другое",
]


def build_categories_keyboard(action_prefix: str = "cat") -> InlineKeyboardMarkup:
    """Build keyboard with food categories.

    Args:
        action_prefix: Prefix for callback data (default: "cat")

    Returns:
        InlineKeyboardMarkup with category buttons in 2 columns.
    """
    buttons = []

    # Create buttons in pairs (2 per row)
    for i in range(0, len(FOOD_CATEGORIES), 2):
        row = []
        for j in range(2):
            if i + j < len(FOOD_CATEGORIES):
                category = FOOD_CATEGORIES[i + j]
                row.append(InlineKeyboardButton(text=category, callback_data=f"{action_prefix}:{category}"))
        buttons.append(row)

    # Add search prompt button
    buttons.append([InlineKeyboardButton(text="🔍 Поиск по названию", callback_data="search_prompt")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_ingredient_search_results(
    ingredients: list[Ingredient],
    query: str = "",
    show_add_custom: bool = True,
    action_prefix: str = "ing",
) -> InlineKeyboardMarkup:
    """Build keyboard with search results.

    Args:
        ingredients: List of found ingredients (max 10).
        query: Search query (for context)
        show_add_custom: Whether to show "Add custom" button.
        action_prefix: Prefix for callback data (default: "ing")

    Returns:
        InlineKeyboardMarkup with ingredient buttons.
    """
    buttons = []

    # Add ingredient buttons (max 10)
    for ingredient in ingredients[:10]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{ingredient.name} ({ingredient.category})", callback_data=f"{action_prefix}:{ingredient.id}"
                )
            ]
        )

    # Add "Nothing fits" button
    if show_add_custom:
        buttons.append([InlineKeyboardButton(text="❌ Ничего не подошло (Добавить своё)", callback_data="add_custom")])

    # Add back button
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_category_ingredients_keyboard(
    ingredients: list[Ingredient],
    category: str,
    action_prefix: str = "ing",
) -> InlineKeyboardMarkup:
    """Build keyboard with top ingredients from category.

    Args:
        ingredients: List of ingredients from category (max 20).
        category: Category name for callback.
        action_prefix: Prefix for callback data (default: "ing")

    Returns:
        InlineKeyboardMarkup with ingredient buttons.
    """
    buttons = []

    # Add ingredient buttons (max 20)
    for ingredient in ingredients[:20]:
        buttons.append([InlineKeyboardButton(text=ingredient.name, callback_data=f"{action_prefix}:{ingredient.id}")])

    # Add search and back buttons
    buttons.append([InlineKeyboardButton(text="🔍 Поиск в категории", callback_data=f"search_in_cat:{category}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
