"""Handlers for food-related commands and interactions."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import Ingredient, User
from allergo_trace_bot.keyboards.food import (
    FOOD_CATEGORIES,
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
    waiting_for_custom_category_name = State()  # Waiting for custom category name input
    waiting_for_aliases = State()  # Waiting for aliases input (optional)
    viewing_ingredient = State()  # Viewing ingredient details
    editing_aliases = State()  # Editing aliases for existing ingredient


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
        .where(or_(Ingredient.user_id.is_(None), Ingredient.user_id == user_id))
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

    user_id = message.from_user.id
    search_pattern = f"%{query}%"

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(
            and_(
                or_(
                    Ingredient.user_id.is_(None),
                    Ingredient.user_id == user_id,
                ),
                or_(
                    Ingredient.name.ilike(search_pattern),
                    func.json_array_length(Ingredient.aliases) > 0,
                ),
            )
        )
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(50)  # Get more to filter in Python
    )
    all_ingredients = ingredient_query_result.scalars().all()

    # Filter in Python to check aliases properly
    ingredients = []
    for ing in all_ingredients:
        # Check name match
        if query in ing.name.lower():
            ingredients.append(ing)
            continue
        # Check aliases match
        if ing.aliases:
            for alias in ing.aliases:
                if query in alias.lower():
                    ingredients.append(ing)
                    break
        if len(ingredients) >= 10:
            break

    if not ingredients:
        # Show option to search again or add custom
        # Save the search query for later use
        await state.update_data(last_search_query=query)
        await state.set_state(FoodStates.waiting_for_search)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Искать еще раз", callback_data="search_prompt")],
                [InlineKeyboardButton(text="➕ Добавить свой продукт", callback_data="add_custom")],
                [InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_categories")],
            ]
        )
        await message.answer(
            f"🔍 По запросу <b>«{query}»</b> ничего не найдено.\n\nПопробуйте другой запрос или добавьте свой продукт.",
            reply_markup=keyboard,
        )
    else:
        await state.clear()
        await message.answer(
            f"🔍 Найдено продуктов: <b>{len(ingredients)}</b>\n\nВыберите подходящий:",
            reply_markup=build_ingredient_search_results(ingredients),
        )


@router.callback_query(F.data.startswith("ing:"))
async def select_ingredient(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    db_user: User,
) -> None:
    """Handle ingredient selection - show details with edit option."""
    if callback.data is None or callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    ingredient_id = int(callback.data.split(":", 1)[1])

    # Get ingredient details
    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await callback.answer("❌ Продукт не найден", show_alert=True)
        return

    await state.update_data(viewing_ingredient_id=ingredient_id)
    await state.set_state(FoodStates.viewing_ingredient)

    # Build message with ingredient details
    aliases_text = ", ".join(ingredient.aliases) if ingredient.aliases else "нет"
    ownership = "личный" if ingredient.user_id == db_user.id else "из справочника"

    message_text = (
        f"📦 <b>{ingredient.name}</b>\\n\\n"
        f"📁 Категория: {ingredient.category}\\n"
        f"🏷 Алиасы: {aliases_text}\\n"
        f"📌 Тип: {ownership}\\n"
    )

    buttons = []

    # Only allow editing aliases for user's own ingredients
    if ingredient.user_id == db_user.id:
        buttons.append([InlineKeyboardButton(text="✏️ Редактировать алиасы", callback_data="edit_aliases")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(message_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "search_prompt", StateFilter(FoodStates.waiting_for_search))
async def search_again_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to search again."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodStates.waiting_for_search)
    await callback.message.edit_text("🔍 <b>Поиск продуктов</b>\n\nВведите название продукта для поиска:")
    await callback.answer()


@router.callback_query(F.data == "add_custom", StateFilter(FoodStates.waiting_for_search))
async def add_custom_ingredient_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start custom ingredient creation flow."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    # Get last search query to suggest as ingredient name
    data = await state.get_data()
    last_query = data.get("last_search_query", "")

    if last_query:
        # Offer to use the search query as the name
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"✅ Использовать «{last_query}»",
                        callback_data="use_search_query",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Ввести другое название",
                        callback_data="enter_custom_name",
                    )
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="search_prompt")],
            ]
        )
        await state.set_state(FoodStates.waiting_for_custom_name)
        await callback.message.edit_text(
            f"➕ <b>Добавление своего продукта</b>\n\n"
            f"Вы искали: <b>«{last_query}»</b>\n\n"
            f"Использовать этот запрос как название продукта или ввести другое?",
            reply_markup=keyboard,
        )
    else:
        await state.set_state(FoodStates.waiting_for_custom_name)
        await callback.message.edit_text("➕ <b>Добавление своего продукта</b>\n\nВведите название продукта:")

    await callback.answer()


@router.callback_query(F.data == "use_search_query", StateFilter(FoodStates.waiting_for_custom_name))
async def use_search_query_as_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Use last search query as ingredient name."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    name = data.get("last_search_query", "").strip()

    if not name or len(name) < 2:
        await callback.answer("❌ Некорректное название", show_alert=True)
        return

    await state.update_data(custom_name=name)
    await state.set_state(FoodStates.waiting_for_custom_category)

    # Show categories as buttons
    keyboard = build_categories_keyboard(action_prefix="custom_cat")

    await callback.message.edit_text(
        f"Отлично! Продукт: <b>{name}</b>\n\nТеперь выберите категорию:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "enter_custom_name", StateFilter(FoodStates.waiting_for_custom_name))
async def enter_custom_name_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter custom ingredient name."""
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

    # Show categories as buttons
    keyboard = build_categories_keyboard(action_prefix="custom_cat")

    await message.answer(
        f"Отлично! Продукт: <b>{name}</b>\n\nТеперь выберите категорию:",
        reply_markup=keyboard,
    )


@router.callback_query(
    F.data.startswith("custom_cat:"),
    StateFilter(FoodStates.waiting_for_custom_category),
)
async def process_custom_category_button(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Process custom ingredient category selection and ask for aliases."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    category = callback.data.split(":", 1)[1]

    # Save category
    await state.update_data(custom_category=category)
    await state.set_state(FoodStates.waiting_for_aliases)

    # Get saved name
    data = await state.get_data()
    name = data["custom_name"]

    # Ask for aliases
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_aliases")],
        ]
    )

    await callback.message.edit_text(
        f"📝 Продукт: <b>{name}</b>\n"
        f"📁 Категория: {category}\n\n"
        f"Хотите добавить алиасы (синонимы)?\n\n"
        f"<i>Например, для 'Помидор' это могут быть: томат, черри</i>\n\n"
        f"Введите алиасы через запятую или нажмите 'Пропустить':",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "custom_cat_custom", StateFilter(FoodStates.waiting_for_custom_category))
async def prompt_custom_category_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter custom category name."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodStates.waiting_for_custom_category_name)
    await callback.message.edit_text(
        "📝 <b>Своя категория</b>\n\nВведите название новой категории\n(например: 'Специи', 'Орехи', 'Соусы'):"
    )
    await callback.answer()


@router.message(StateFilter(FoodStates.waiting_for_custom_category_name))
async def process_custom_category_name(message: Message, state: FSMContext) -> None:
    """Process custom category name and ask for aliases."""
    if message.text is None:
        return

    category = message.text.strip()

    if len(category) < 2:
        await message.answer("❌ Название категории должно содержать минимум 2 символа.")
        return

    # Save category
    await state.update_data(custom_category=category)
    await state.set_state(FoodStates.waiting_for_aliases)

    # Get saved name
    data = await state.get_data()
    name = data["custom_name"]

    # Ask for aliases

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_aliases")],
        ]
    )

    await message.answer(
        f"📝 Продукт: <b>{name}</b>\n"
        f"📁 Категория: {category}\n\n"
        f"Хотите добавить алиасы (синонимы)?\n\n"
        f"<i>Например, для 'Помидор' это могут быть: томат, черри</i>\n\n"
        f"Введите алиасы через запятую или нажмите 'Пропустить':",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "skip_aliases", StateFilter(FoodStates.waiting_for_aliases))
async def skip_aliases(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Skip aliases and create ingredient without them."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.from_user is None:
        return

    data = await state.get_data()
    name = data["custom_name"]
    category = data["custom_category"]
    user_id = callback.from_user.id

    ingredient_query_result = await session.execute(
        select(Ingredient).where(Ingredient.name == name, Ingredient.user_id == user_id)
    )
    existing_ingredient = ingredient_query_result.scalar_one_or_none()

    if existing_ingredient:
        await callback.message.edit_text(
            f"❌ У вас уже есть продукт <b>{name}</b> в категории <b>{existing_ingredient.category}</b>."
        )
        await state.clear()
        await callback.answer()
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

    await callback.message.edit_text(
        f"✅ Продукт успешно добавлен!\n\n"
        f"<b>{name}</b>\n"
        f"Категория: {category}\n\n"
        f"Теперь вы можете найти его через поиск или в категории."
    )
    await callback.answer()


@router.message(StateFilter(FoodStates.waiting_for_aliases))
async def process_aliases(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Process aliases input and create ingredient."""
    if message.text is None or message.from_user is None:
        return

    # Parse aliases from comma-separated input
    aliases_text = message.text.strip()
    aliases = [alias.strip() for alias in aliases_text.split(",") if alias.strip()]

    # Get saved data
    data = await state.get_data()
    name = data["custom_name"]
    category = data["custom_category"]
    user_id = message.from_user.id

    ingredient_query_result = await session.execute(
        select(Ingredient).where(Ingredient.name == name, Ingredient.user_id == user_id)
    )
    existing_ingredient = ingredient_query_result.scalar_one_or_none()

    if existing_ingredient:
        await message.answer(
            f"❌ У вас уже есть продукт <b>{name}</b> в категории <b>{existing_ingredient.category}</b>."
        )
        await state.clear()
        return

    new_ingredient = Ingredient(
        name=name,
        category=category,
        aliases=aliases,
        user_id=user_id,
    )
    session.add(new_ingredient)
    await session.commit()
    await session.refresh(new_ingredient)

    await state.clear()

    aliases_display = ", ".join(aliases) if aliases else "нет"
    await message.answer(
        f"✅ Продукт успешно добавлен!\n\n"
        f"<b>{name}</b>\n"
        f"Категория: {category}\n"
        f"Алиасы: {aliases_display}\n\n"
        f"Теперь вы можете найти его через поиск или в категории."
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
    existing_ingredient_query = await session.execute(
        select(Ingredient).where(Ingredient.name == name, Ingredient.user_id == user_id)
    )
    existing_ingredient = existing_ingredient_query.scalar_one_or_none()

    if existing_ingredient:
        await message.answer(
            f"❌ У вас уже есть продукт <b>{name}</b> в категории <b>{existing_ingredient.category}</b>."
        )
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


@router.callback_query(F.data == "edit_aliases", StateFilter(FoodStates.viewing_ingredient))
async def edit_aliases_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Start editing aliases for an ingredient."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    ingredient_id = data.get("viewing_ingredient_id")

    if not ingredient_id:
        await callback.answer("❌ Ошибка: продукт не найден", show_alert=True)
        return

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await callback.answer("❌ Продукт не найден", show_alert=True)
        return

    await state.set_state(FoodStates.editing_aliases)

    current_aliases = ", ".join(ingredient.aliases) if ingredient.aliases else "нет"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить все алиасы", callback_data="clear_aliases")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit_aliases")],
        ]
    )

    await callback.message.edit_text(
        f"✏️ <b>Редактирование алиасов</b>\n\n"
        f"Продукт: <b>{ingredient.name}</b>\n"
        f"Текущие алиасы: {current_aliases}\n\n"
        f"Введите новые алиасы через запятую.\n"
        f"<i>Текущие алиасы будут заменены на новые.</i>\n\n"
        f"Например: томат, черри, помидорка",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "clear_aliases", StateFilter(FoodStates.editing_aliases))
async def clear_aliases(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Clear all aliases from ingredient."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    ingredient_id = data.get("viewing_ingredient_id")

    if not ingredient_id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await callback.answer("❌ Продукт не найден", show_alert=True)
        return

    ingredient.aliases = []
    await session.commit()
    await state.clear()

    await callback.message.edit_text(f"✅ <b>Алиасы удалены</b>\n\nПродукт: <b>{ingredient.name}</b>\nАлиасы: нет")
    await callback.answer()


@router.callback_query(F.data == "cancel_edit_aliases", StateFilter(FoodStates.editing_aliases))
async def cancel_edit_aliases(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Cancel alias editing and return to ingredient view."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    ingredient_id = data.get("viewing_ingredient_id")

    if not ingredient_id:
        await state.clear()
        await callback.message.edit_text("❌ Отменено")
        await callback.answer()
        return

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await state.clear()
        await callback.message.edit_text("❌ Продукт не найден")
        await callback.answer()
        return

    await state.set_state(FoodStates.viewing_ingredient)

    aliases_text = ", ".join(ingredient.aliases) if ingredient.aliases else "нет"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать алиасы", callback_data="edit_aliases")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories")],
        ]
    )

    await callback.message.edit_text(
        f"📦 <b>{ingredient.name}</b>\n\n📁 Категория: {ingredient.category}\n🏷 Алиасы: {aliases_text}\n📌 Тип: личный",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.message(StateFilter(FoodStates.editing_aliases))
async def process_alias_edit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Process new aliases for ingredient."""
    if message.text is None:
        return

    aliases_text = message.text.strip()
    new_aliases = [alias.strip() for alias in aliases_text.split(",") if alias.strip()]

    data = await state.get_data()
    ingredient_id = data.get("viewing_ingredient_id")

    if not ingredient_id:
        await message.answer("❌ Ошибка: продукт не найден")
        await state.clear()
        return

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await message.answer("❌ Продукт не найден")
        await state.clear()
        return

    # Update aliases
    ingredient.aliases = new_aliases
    await session.commit()
    await state.clear()

    aliases_display = ", ".join(new_aliases) if new_aliases else "нет"

    await message.answer(
        f"✅ <b>Алиасы обновлены!</b>\n\n"
        f"Продукт: <b>{ingredient.name}</b>\n"
        f"Новые алиасы: {aliases_display}\n\n"
        f"Теперь вы можете искать продукт по этим алиасам."
    )
