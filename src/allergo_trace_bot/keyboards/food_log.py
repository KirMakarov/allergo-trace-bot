"""Keyboard builders for food logging."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from allergo_trace_bot.database.models import Dish, Ingredient
from allergo_trace_bot.utils.datetime_utils import get_utc_now


def build_dish_selection_keyboard(dishes: list[Dish]) -> InlineKeyboardMarkup:
    """Build keyboard for selecting dish to log.

    Args:
        dishes: List of Dish objects

    Returns:
        InlineKeyboardMarkup with dish selection buttons
    """
    buttons = []

    buttons.append(
        [
            InlineKeyboardButton(
                text="🥗 Log Food Item",
                callback_data="log:select_product",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="✏️ Enter Manually",
                callback_data="log:enter_manual",
            )
        ]
    )

    if dishes:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="── Prepared Dishes ──",
                    callback_data="log:separator",
                )
            ]
        )

    current_category = None

    for dish in dishes:
        # Add category header
        if dish.category != current_category:
            current_category = dish.category
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📁 {current_category}",
                        callback_data=f"log_category:{current_category}",
                    )
                ]
            )

        # Add dish button
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🍽 {dish.name}",
                    callback_data=f"log_dish:{dish.id}",
                )
            ]
        )

    # Add cancel button
    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="log:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_confirm_log_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for confirming food log entry.

    Returns:
        InlineKeyboardMarkup with Yes/Edit/Cancel buttons
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Yes, Save",
                callback_data="log:confirm",
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Edit Ingredients",
                callback_data="log:edit",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="log:cancel",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_edit_ingredients_keyboard(
    ingredients: list[Ingredient],
) -> InlineKeyboardMarkup:
    """Build keyboard for editing ingredients before logging.

    Args:
        ingredients: List of Ingredient objects

    Returns:
        InlineKeyboardMarkup with remove buttons for each ingredient
    """
    buttons = []

    # Add remove button for each ingredient
    for ingredient in ingredients:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"➖ {ingredient.name}",
                    callback_data=f"log:remove_ing:{ingredient.id}",
                )
            ]
        )

    # Add ingredient button (for future implementation)
    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Add Ingredient",
                callback_data="log:add_ingredient",
            )
        ]
    )

    # Done editing button
    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Done",
                callback_data="log:done_editing",
            )
        ]
    )

    # Cancel button
    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="log:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_time_selection_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for selecting meal time.

    Returns:
        InlineKeyboardMarkup with time selection options
    """

    now = get_utc_now()

    buttons = [
        [
            InlineKeyboardButton(
                text=f"⏰ Now ({now.strftime('%H:%M')})",
                callback_data="log:time:now",
            )
        ],
        [
            InlineKeyboardButton(
                text="🌅 Morning (08:00)",
                callback_data="log:time:morning",
            )
        ],
        [
            InlineKeyboardButton(
                text="☀️ Afternoon (13:00)",
                callback_data="log:time:afternoon",
            )
        ],
        [
            InlineKeyboardButton(
                text="🌙 Evening (19:00)",
                callback_data="log:time:evening",
            )
        ],
    ]

    # Add some specific time options based on current time

    # Add buttons for recent times (last 2-3 hours in 30-min intervals)
    time_options = []
    for hours_ago in [1, 2, 3]:
        time = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
        time = time.replace(hour=max(0, time.hour - hours_ago))
        if 0 <= time.hour <= 23:
            time_options.append(
                InlineKeyboardButton(
                    text=f"🕐 {time.strftime('%H:%M')}",
                    callback_data=f"log:time:{time.strftime('%H:%M')}",
                )
            )

    # Add time options in pairs
    for i in range(0, len(time_options), 2):
        row = time_options[i : i + 2]
        if row:
            buttons.append(row)

    # Cancel button
    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Back",
                callback_data="log:back_to_confirm",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
