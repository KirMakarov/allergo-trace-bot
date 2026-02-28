"""Keyboards for analytics feature."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from allergo_trace_bot.services.analytics import IngredientOccurrence


def build_time_window_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for selecting analysis time window.

    Returns:
        InlineKeyboardMarkup with time window options
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏱ 2 часа (быстрая реакция)",
                    callback_data="analyze:window:2",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏱ 6 часов",
                    callback_data="analyze:window:6",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏱ 12 часов",
                    callback_data="analyze:window:12",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 24 часа (замедленная реакция)",
                    callback_data="analyze:window:24",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="analyze:cancel",
                )
            ],
        ]
    )


def build_report_actions_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for actions after viewing report.

    Returns:
        InlineKeyboardMarkup with report action buttons
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛡 Отметить безопасные продукты",
                    callback_data="analyze:safe:show",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Другое временное окно",
                    callback_data="analyze:rerun",
                )
            ],
        ]
    )


def build_safe_ingredients_selection_keyboard(
    candidates: list[IngredientOccurrence],
    selected_ids: set[int],
) -> InlineKeyboardMarkup:
    """Build keyboard for selecting safe ingredients.

    Args:
        candidates: List of candidate ingredients
        selected_ids: Set of currently selected ingredient IDs

    Returns:
        InlineKeyboardMarkup with checkboxes and control buttons
    """
    buttons: list[list[InlineKeyboardButton]] = []

    for candidate in candidates:
        # Checkbox emoji based on selection state
        checkbox = "✅" if candidate.ingredient_id in selected_ids else "☐"
        risk_text = f"{candidate.risk_score:.0f}%"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{checkbox} {candidate.ingredient_name} ({risk_text})",
                    callback_data=f"analyze:safe:toggle:{candidate.ingredient_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Готово",
                callback_data="analyze:safe:save",
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="analyze:safe:cancel",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_no_safe_candidates_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard when no safe candidates available.

    Returns:
        InlineKeyboardMarkup with back button
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к анализу",
                    callback_data="analyze:rerun",
                )
            ]
        ]
    )
