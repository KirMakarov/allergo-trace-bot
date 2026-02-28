"""Keyboard builders for dish management."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from allergo_trace_bot.config import DISH_CATEGORIES
from allergo_trace_bot.database.models import Dish


def build_dish_categories_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with dish categories.

    Returns:
        InlineKeyboardMarkup with category buttons in 2 columns.
    """
    buttons = []

    for i in range(0, len(DISH_CATEGORIES), 2):
        row = []
        for j in range(2):
            if i + j < len(DISH_CATEGORIES):
                category = DISH_CATEGORIES[i + j]
                row.append(InlineKeyboardButton(text=category, callback_data=f"dish_cat:{category}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Custom Category", callback_data="dish_cat_custom")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_dish_composition_keyboard(
    ingredient_ids: list[int],
    dish_name: str,
    category: str,
) -> InlineKeyboardMarkup:
    """Build keyboard for dish composition management.

    Args:
        ingredient_ids: List of ingredient IDs in the dish
        dish_name: Name of the dish
        category: Category of the dish

    Returns:
        InlineKeyboardMarkup with buttons to add/remove ingredients and save
    """
    buttons = []

    # Add ingredient button
    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Add Ingredient",
                callback_data="dish:add_ingredient",
            )
        ]
    )

    # Remove ingredient buttons (if any)
    if ingredient_ids:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="➖ Remove Ingredient",
                    callback_data="dish:show_remove_menu",
                )
            ]
        )

        # Show remove buttons for each ingredient
        # Note: We'll show them inline with ingredient names in the message
        # But for now, let's use search to add back functionality

    # Search button
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔍 Search Ingredient",
                callback_data="dish:search_ingredient",
            )
        ]
    )

    if ingredient_ids:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Save Dish",
                    callback_data="dish:save",
                )
            ]
        )
    else:
        # Option to save without specifying ingredients
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Save without Ingredients",
                    callback_data="dish:save_empty",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="dish:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_dish_list_keyboard(
    dishes: list[Dish],
    action_prefix: str = "view_dish",
) -> InlineKeyboardMarkup:
    """Build keyboard with list of dishes grouped by category.

    Args:
        dishes: List of Dish objects
        action_prefix: Prefix for callback data (default: "view_dish")

    Returns:
        InlineKeyboardMarkup with dish buttons
    """
    buttons = []
    current_category = None

    for dish in dishes:
        # Add category header as a disabled button
        if dish.category != current_category:
            current_category = dish.category
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📁 {current_category}",
                        callback_data=f"category_header:{current_category}",
                    )
                ]
            )

        # Add dish button
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🍽 {dish.name}",
                    callback_data=f"{action_prefix}:{dish.id}",
                )
            ]
        )

    if not buttons:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📝 Create First Dish",
                    callback_data="create_first_dish",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
