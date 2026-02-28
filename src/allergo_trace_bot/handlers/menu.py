"""Handlers for menu, help and start commands."""

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, BotCommandScopeDefault, Message

from allergo_trace_bot.keyboards.menu import get_main_menu_keyboard

router = Router(name="menu")


# Bot commands for the menu button (blue button left of input field)
BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="log_food", description="🍽 Записать приём пищи"),
    BotCommand(command="my_dishes", description="📋 Мои блюда"),
    BotCommand(command="food", description="🥗 Добавить продукт в справочник"),
    BotCommand(command="new_dish", description="🍳 Создать новое блюдо"),
    BotCommand(command="analyze", description="📊 Анализ корреляций"),
    BotCommand(command="settings", description="⚙️ Настройки (часовой пояс, напоминания)"),
    BotCommand(command="help", description="❓ Справка"),
    BotCommand(command="stop", description="🛑 Отменить текущую операцию"),
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
        "👋 <b>Добро пожаловать в AllergoTrace!</b>\n\n"
        "Я помогу вам вести дневник питания и отслеживать связь "
        "между едой и симптомами аллергии.\n\n"
        "<b>Что я умею:</b>\n"
        "🍽 Записывать приёмы пищи\n"
        "🍳 Создавать шаблоны блюд\n"
        "📊 Анализировать корреляции\n"
        "⏰ Напоминать о записи еды\n\n"
        "Используйте кнопки ниже или команды из меню.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Handle /help command.

    Shows detailed help with all commands and features.
    """
    await message.answer(
        "📖 <b>Справка по боту AllergoTrace</b>\n\n"
        "<b>🍽 Основные команды:</b>\n"
        "/log_food — Записать приём пищи\n"
        "/my_dishes — Просмотреть мои блюда\n"
        "/food — Добавить продукт в справочник\n"
        "/new_dish — Создать новое блюдо (шаблон)\n"
        "/analyze — Анализ корреляций еды и симптомов\n"
        "/settings — Настроить часовой пояс и напоминания\n\n"
        "<b>🛠 Служебные команды:</b>\n"
        "/stop — Отменить текущую операцию\n"
        "/help — Показать эту справку\n\n"
        "<b>✨ Возможности:</b>\n"
        "• Создавайте личные продукты с алиасами для быстрого поиска\n"
        "• Собирайте блюда из продуктов как шаблоны\n"
        "• Изменяйте состав блюда при записи\n"
        "• Ведите дневник питания с историей\n"
        "• Настраивайте напоминания по своему времени\n"
        "• Анализируйте связь продуктов с симптомами\n\n",
        reply_markup=get_main_menu_keyboard(),
    )
