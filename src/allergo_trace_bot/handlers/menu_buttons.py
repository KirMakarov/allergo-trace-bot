"""Router for handling reply keyboard menu buttons."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import User
from allergo_trace_bot.handlers.analytics import cmd_analyze
from allergo_trace_bot.handlers.dish import cmd_my_dishes, cmd_new_dish
from allergo_trace_bot.handlers.food_log import cmd_log_food
from allergo_trace_bot.handlers.timezone import cmd_settings
from allergo_trace_bot.keyboards.food import build_categories_keyboard
from allergo_trace_bot.keyboards.menu import get_main_menu_keyboard

router = Router(name="menu_buttons")


@router.message(F.text == "🍽 Log Food")
async def btn_log_food(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Handle 'Log Food' button - same as /log_food command."""
    await cmd_log_food(message, state, session, db_user)


@router.message(F.text == "📋 My Dishes")
async def btn_my_dishes(message: Message, session: AsyncSession, db_user: User) -> None:
    """Handle 'My Dishes' button - same as /my_dishes command."""
    await cmd_my_dishes(message, session, db_user)


@router.message(F.text == "🥗 Add Product")
async def btn_add_food(message: Message) -> None:
    """Handle 'Add Product' button - same as /food command."""
    await message.answer(
        "🍽 <b>Add Product</b>\n\nSelect a category or use search:",
        reply_markup=build_categories_keyboard(),
    )


@router.message(F.text == "🍳 New Dish")
async def btn_new_dish(message: Message, state: FSMContext) -> None:
    """Handle 'New Dish' button - same as /new_dish command."""
    await cmd_new_dish(message, state)


@router.message(F.text == "📊 Analysis")
async def btn_analyze(message: Message, state: FSMContext) -> None:
    """Handle 'Analysis' button - same as /analyze command."""
    await cmd_analyze(message, state)


@router.message(F.text == "⚙️ Settings")
async def btn_settings(message: Message, session: AsyncSession, db_user: User) -> None:
    """Handle 'Settings' button - same as /settings command."""
    await cmd_settings(message, session, db_user)


@router.message(F.text == "❓ Help")
async def btn_help(message: Message) -> None:
    """Handle 'Help' button - same as /help command."""
    await message.answer(
        "📖 <b>AllergoTrace Bot Help</b>\n\n"
        "<b>🍽 Main Commands:</b>\n"
        "/log_food — Log a meal\n"
        "/my_dishes — View my dishes\n"
        "/food — Add product to directory\n"
        "/new_dish — Create new dish (template)\n"
        "/analyze — Analyze food-symptom correlations\n"
        "/settings — Configure timezone and reminders\n\n"
        "<b>🛠 Utility Commands:</b>\n"
        "/stop — Cancel current operation\n"
        "/help — Show this help\n\n"
        "<b>✨ Features:</b>\n"
        "• Create personal products with aliases for quick search\n"
        "• Assemble dishes from products as templates\n"
        "• Edit dish composition while logging\n"
        "• Keep a food diary with history\n"
        "• Configure reminders for your timezone\n"
        "• Analyze connection between food and symptoms\n\n",
        reply_markup=get_main_menu_keyboard(),
    )
