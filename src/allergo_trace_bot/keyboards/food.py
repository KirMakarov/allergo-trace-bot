"""Keyboards for food-related interactions."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from allergo_trace_bot.config import FOOD_CATEGORIES
from allergo_trace_bot.database.models import Ingredient

__all__ = [
    "FOOD_CATEGORIES",
    "build_categories_keyboard",
    "build_ingredient_search_results",
    "build_category_ingredients_keyboard",
]


def build_categories_keyboard(
    action_prefix: str = "cat",
    show_custom_category: bool = True,
) -> InlineKeyboardMarkup:
    """Build keyboard with food categories.

    Args:
        action_prefix: Prefix for callback data (default: "cat")
        show_custom_category: Whether to show "Add custom category" button

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

    if show_custom_category:
        buttons.append([InlineKeyboardButton(text="➕ Custom Category", callback_data=f"{action_prefix}_custom")])

    # Add search prompt button
    buttons.append([InlineKeyboardButton(text="🔍 Search by Name", callback_data="search_prompt")])

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
                    text=f"{ingredient.name} ({ingredient.category})",
                    callback_data=f"{action_prefix}:{ingredient.id}",
                )
            ]
        )

    # Add "Nothing fits" button
    if show_add_custom:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="❌ Nothing fits (Add custom)",
                    callback_data="add_custom",
                )
            ]
        )

    # Add back button
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Categories", callback_data="back_to_categories")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_category_ingredients_keyboard(
    ingredients: list[Ingredient],
    category: str,
    action_prefix: str = "ing",
    search_callback: str | None = None,
    back_callback: str = "back_to_categories",
) -> InlineKeyboardMarkup:
    """Build keyboard with top ingredients from category.

    Args:
        ingredients: List of ingredients from category (max 20).
        category: Category name for callback.
        action_prefix: Prefix for callback data (default: "ing")
        search_callback: Custom callback for search button. If None, uses "search_in_cat:{category}"
        back_callback: Callback for back button (default: "back_to_categories")

    Returns:
        InlineKeyboardMarkup with ingredient buttons.
    """
    buttons = []

    # Add ingredient buttons (max 20)
    for ingredient in ingredients[:20]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=ingredient.name,
                    callback_data=f"{action_prefix}:{ingredient.id}",
                )
            ]
        )

    # Add search and back buttons
    search_cb = search_callback if search_callback else f"search_in_cat:{category}"
    buttons.append([InlineKeyboardButton(text="🔍 Search in Category", callback_data=search_cb)])

    buttons.append([InlineKeyboardButton(text="⬅️ Back to Categories", callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
