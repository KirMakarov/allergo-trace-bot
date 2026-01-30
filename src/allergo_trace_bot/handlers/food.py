"""Handlers for food-related commands and interactions."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import Ingredient
from allergo_trace_bot.keyboards.food import (
    build_categories_keyboard,
    build_category_ingredients_keyboard,
    build_ingredient_search_results,
)

router = Router(name="food")


class FoodStates(StatesGroup):
    """States for food input flow."""

    waiting_for_search = State()  # Waiting for search query
    waiting_for_custom_name = State()  # Waiting for custom ingredient name
    waiting_for_custom_category = State()  # Waiting for custom ingredient category


@router.message(Command("food"))
async def cmd_food(message: Message) -> None:
    """Handle /food command - show category selection."""
    await message.answer(
        "🍽 <b>Добавление продукта</b>\n\nВыберите категорию или воспользуйтесь поиском:",
        reply_markup=build_categories_keyboard(),
    )


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to category selection."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    await callback.message.edit_text(
        "🍽 <b>Добавление продукта</b>\n\nВыберите категорию или воспользуйтесь поиском:",
        reply_markup=build_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def select_category(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Handle category selection - show top ingredients."""
    if callback.data is None or callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    category = callback.data.split(":", 1)[1]

    # Get top 20 ingredients from category (global + user's)
    user_id = callback.from_user.id
    result = await session.execute(
        select(Ingredient)
        .where(Ingredient.category == category)
        .where(or_(Ingredient.user_id == None, Ingredient.user_id == user_id))  # noqa: E711
        .order_by(Ingredient.user_id.desc(), Ingredient.name)  # User's first, then global
        .limit(20)
    )
    ingredients = list(result.scalars().all())

    if not ingredients:
        await callback.message.edit_text(
            f"В категории <b>{category}</b> пока нет продуктов.\nИспользуйте поиск или добавьте свой продукт.",
            reply_markup=build_categories_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"📂 <b>{category}</b>\n\nВыберите продукт:",
            reply_markup=build_category_ingredients_keyboard(ingredients, category),
        )

    await callback.answer()


@router.callback_query(F.data == "search_prompt")
async def search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter search query."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodStates.waiting_for_search)
    await callback.message.edit_text(
        "🔍 <b>Поиск продукта</b>\n\nВведите название продукта для поиска:\n(Например: помидор, молоко, яблоко)"
    )
    await callback.answer()


@router.message(StateFilter(FoodStates.waiting_for_search))
async def process_search(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Process search query and show results."""
    if message.text is None or message.from_user is None:
        return

    query = message.text.strip().lower()

    if len(query) < 2:
        await message.answer("❌ Введите хотя бы 2 символа для поиска.")
        return

    # Search in name and aliases
    user_id = message.from_user.id
    search_pattern = f"%{query}%"

    result = await session.execute(
        select(Ingredient)
        .where(
            or_(
                Ingredient.name.ilike(search_pattern),
                Ingredient.aliases.cast(str).ilike(search_pattern),  # Search in JSON array
            )
        )
        .where(or_(Ingredient.user_id == None, Ingredient.user_id == user_id))  # noqa: E711
        .order_by(Ingredient.user_id.desc(), Ingredient.name)  # User's first
        .limit(10)
    )
    ingredients = list(result.scalars().all())

    await state.clear()

    if not ingredients:
        await message.answer(
            f"🔍 По запросу <b>«{query}»</b> ничего не найдено.\n\nПопробуйте другой запрос или добавьте свой продукт.",
            reply_markup=build_ingredient_search_results([], show_add_custom=True),
        )
    else:
        await message.answer(
            f"🔍 Найдено продуктов: <b>{len(ingredients)}</b>\n\nВыберите подходящий:",
            reply_markup=build_ingredient_search_results(ingredients),
        )


@router.callback_query(F.data.startswith("ing:"))
async def select_ingredient(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Handle ingredient selection."""
    if callback.data is None or callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    ingredient_id = int(callback.data.split(":", 1)[1])

    # Get ingredient details
    result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = result.scalar_one_or_none()

    if not ingredient:
        await callback.answer("❌ Продукт не найден", show_alert=True)
        return

    # TODO: Add to current meal/dish (будет реализовано позже)
    # Пока просто показываем успешное добавление
    await callback.message.edit_text(
        f"✅ Добавлен продукт:\n\n"
        f"<b>{ingredient.name}</b>\n"
        f"Категория: {ingredient.category}\n\n"
        f"<i>Функционал добавления в блюдо будет реализован на следующем этапе.</i>"
    )
    await callback.answer()


@router.callback_query(F.data == "add_custom")
async def add_custom_ingredient_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start custom ingredient creation flow."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodStates.waiting_for_custom_name)
    await callback.message.edit_text("➕ <b>Добавление своего продукта</b>\n\nВведите название продукта:")
    await callback.answer()


@router.message(StateFilter(FoodStates.waiting_for_custom_name))
async def process_custom_name(message: Message, state: FSMContext) -> None:
    """Process custom ingredient name and ask for category."""
    if message.text is None:
        return

    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название должно содержать минимум 2 символа.")
        return

    await state.update_data(custom_name=name)
    await state.set_state(FoodStates.waiting_for_custom_category)

    # Show categories as text options
    from allergo_trace_bot.keyboards.food import FOOD_CATEGORIES

    categories_text = "\n".join(f"• {cat}" for cat in FOOD_CATEGORIES)

    await message.answer(
        f"Отлично! Продукт: <b>{name}</b>\n\nТеперь выберите категорию (напишите название):\n\n{categories_text}"
    )


@router.message(StateFilter(FoodStates.waiting_for_custom_category))
async def process_custom_category(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Process custom ingredient category and save to DB."""
    if message.text is None or message.from_user is None:
        return

    from allergo_trace_bot.keyboards.food import FOOD_CATEGORIES

    category = message.text.strip()

    # Validate category
    if category not in FOOD_CATEGORIES:
        await message.answer(
            "❌ Пожалуйста, выберите одну из предложенных категорий:\n\n"
            + "\n".join(f"• {cat}" for cat in FOOD_CATEGORIES)
        )
        return

    # Get saved name
    data = await state.get_data()
    name = data["custom_name"]
    user_id = message.from_user.id

    # Check if ingredient already exists for this user
    result = await session.execute(select(Ingredient).where(Ingredient.name == name, Ingredient.user_id == user_id))
    existing = result.scalar_one_or_none()

    if existing:
        await message.answer(f"❌ У вас уже есть продукт <b>{name}</b> в категории <b>{existing.category}</b>.")
        await state.clear()
        return

    # Create new ingredient
    new_ingredient = Ingredient(
        name=name,
        category=category,
        aliases=[],
        user_id=user_id,
    )
    session.add(new_ingredient)
    await session.commit()
    await session.refresh(new_ingredient)

    await state.clear()

    await message.answer(
        f"✅ Продукт успешно добавлен!\n\n"
        f"<b>{name}</b>\n"
        f"Категория: {category}\n\n"
        f"Теперь вы можете найти его через поиск или в категории."
    )
