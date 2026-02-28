"""Handlers for menu, help and start commands."""

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, BotCommandScopeDefault, Message

from allergo_trace_bot.keyboards.menu import get_main_menu_keyboard

router = Router(name="menu")


# Bot commands for the menu button (blue button left of input field)
BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="log_food", description="🍽 Log a meal"),
    BotCommand(command="my_dishes", description="📋 My dishes"),
    BotCommand(command="food", description="🥗 Add product to directory"),
    BotCommand(command="new_dish", description="🍳 Create new dish"),
    BotCommand(command="analyze", description="📊 Correlation analysis"),
    BotCommand(command="settings", description="⚙️ Settings (timezone, reminders)"),
    BotCommand(command="help", description="❓ Help"),
    BotCommand(command="stop", description="🛑 Cancel current operation"),
]


async def set_bot_commands(bot: Bot) -> None:
    """
    Set bot commands for the menu button.

    This configures the blue menu button (☰) that appears
    to the left of the text input field in Telegram.
    """
    await bot.set_my_commands(
        commands=BOT_COMMANDS,
        scope=BotCommandScopeDefault(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Handle /start command.

    Shows welcome message and the main menu keyboard.
    """
    await state.clear()

    await message.answer(
        "👋 <b>Welcome to AllergoTrace!</b>\n\n"
        "I will help you keep a food diary and track the connection "
        "between food and allergy symptoms.\n\n"
        "<b>What I can do:</b>\n"
        "🍽 Log meals\n"
        "🍳 Create dish templates\n"
        "📊 Analyze correlations\n"
        "⏰ Remind to log food\n\n"
        "Use the buttons below or commands from the menu.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Handle /help command.

    Shows detailed help with all commands and features.
    """
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
