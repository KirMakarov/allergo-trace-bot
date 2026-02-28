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


@router.message(F.text == "🍽 Записать еду")
async def btn_log_food(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Handle 'Записать еду' button - same as /log_food command."""
    await cmd_log_food(message, state, session, db_user)


@router.message(F.text == "📋 Мои блюда")
async def btn_my_dishes(message: Message, session: AsyncSession, db_user: User) -> None:
    """Handle 'Мои блюда' button - same as /my_dishes command."""
    await cmd_my_dishes(message, session, db_user)


@router.message(F.text == "🥗 Добавить продукт")
async def btn_add_food(message: Message) -> None:
    """Handle 'Добавить продукт' button - same as /food command."""
    await message.answer(
        "🍽 <b>Добавление продукта</b>\n\nВыберите категорию или воспользуйтесь поиском:",
        reply_markup=build_categories_keyboard(),
    )


@router.message(F.text == "🍳 Новое блюдо")
async def btn_new_dish(message: Message, state: FSMContext) -> None:
    """Handle 'Новое блюдо' button - same as /new_dish command."""
    await cmd_new_dish(message, state)


@router.message(F.text == "📊 Анализ")
async def btn_analyze(message: Message, state: FSMContext) -> None:
    """Handle 'Анализ' button - same as /analyze command."""
    await cmd_analyze(message, state)


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message, session: AsyncSession, db_user: User) -> None:
    """Handle 'Настройки' button - same as /settings command."""
    await cmd_settings(message, session, db_user)


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    """Handle 'Помощь' button - same as /help command."""
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
