"""Handlers for food logging (recording meals)."""

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardButton, Message
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import (
    Dish,
    DishIngredient,
    FoodLog,
    Ingredient,
    User,
)
from allergo_trace_bot.keyboards.food_log import (
    build_confirm_log_keyboard,
    build_dish_selection_keyboard,
    build_edit_ingredients_keyboard,
)

router = Router(name="food_log")


class FoodLogStates(StatesGroup):
    """States for food logging flow."""

    selecting_dish = State()  # Selecting dish to log
    confirming_log = State()  # Confirming or editing composition
    editing_ingredients = State()  # Editing ingredients before logging
    selecting_time = State()  # Selecting time for the meal
    selecting_product = State()  # Selecting product from database
    searching_product = State()  # Searching product by name
    entering_manual = State()  # Entering product name manually
    asking_save_product = State()  # Asking if to save manual product


@router.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Start food logging - show dish selection or product options."""
    dishes_query_result = await session.execute(
        select(Dish).where(Dish.user_id == db_user.id).order_by(Dish.category, Dish.name)
    )
    dishes = list(dishes_query_result.scalars().all())

    await state.set_state(FoodLogStates.selecting_dish)

    keyboard = build_dish_selection_keyboard(dishes)

    await message.answer(
        "🍽 Что вы съели?\n\n"
        "Выберите способ записи:\n"
        "• <b>Записать продукт</b> - выбрать из базы\n"
        "• <b>Ввести вручную</b> - любой продукт\n"
        "• <b>Готовые блюда</b> - ваши сохраненные блюда",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:select_product", StateFilter(FoodLogStates.selecting_dish))
async def select_product_for_logging(callback: CallbackQuery, state: FSMContext) -> None:
    """Show product categories for selection."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    from allergo_trace_bot.keyboards.food import build_categories_keyboard

    keyboard = build_categories_keyboard(action_prefix="log_cat", show_custom_category=False)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="log:back_to_main")])

    await state.set_state(FoodLogStates.selecting_product)
    await message.edit_text(
        "🥗 <b>Выберите категорию продукта</b>\n\nИли воспользуйтесь поиском:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "log:back_to_main", StateFilter(FoodLogStates))
async def back_to_main_log_menu(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Return to main log food menu."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    dishes_query_result = await session.execute(
        select(Dish).where(Dish.user_id == db_user.id).order_by(Dish.category, Dish.name)
    )
    dishes = list(dishes_query_result.scalars().all())

    await state.set_state(FoodLogStates.selecting_dish)
    keyboard = build_dish_selection_keyboard(dishes)

    await message.edit_text(
        "🍽 Что вы съели?\n\n"
        "Выберите способ записи:\n"
        "• <b>Записать продукт</b> - выбрать из базы\n"
        "• <b>Ввести вручную</b> - любой продукт\n"
        "• <b>Готовые блюда</b> - ваши сохраненные блюда",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("log_cat:"), StateFilter(FoodLogStates.selecting_product))
async def select_product_category(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Show products from selected category."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    category = callback.data.split(":", 1)[1]
    from sqlalchemy import or_

    category_ingredients_query = await session.execute(
        select(Ingredient)
        .where(Ingredient.category == category)
        .where(or_(Ingredient.user_id == None, Ingredient.user_id == db_user.id))  # noqa: E711
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(20)
    )
    ingredients = list(category_ingredients_query.scalars().all())

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    for ing in ingredients:
        buttons.append([InlineKeyboardButton(text=ing.name, callback_data=f"log_ing:{ing.id}")])

    buttons.append([InlineKeyboardButton(text="🔍 Поиск", callback_data="log:search_product")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="log:select_product")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.edit_text(
        f"📁 <b>{category}</b>\n\nВыберите продукт:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "search_prompt", StateFilter(FoodLogStates.selecting_product))
async def search_product_prompt_log(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt to search for product."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodLogStates.searching_product)
    await callback.message.edit_text("🔍 Введите название продукта для поиска:")
    await callback.answer()


@router.callback_query(F.data == "log:search_product", StateFilter(FoodLogStates.selecting_product))
async def search_product_prompt_log_alt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt to search for product (alternative callback)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodLogStates.searching_product)
    await callback.message.edit_text("🔍 Введите название продукта для поиска:")
    await callback.answer()


@router.message(StateFilter(FoodLogStates.searching_product))
async def process_product_search(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process product search query."""
    if message.text is None:
        return

    query = message.text.strip().lower()

    if len(query) < 2:
        await message.answer("❌ Введите хотя бы 2 символа для поиска.")
        return

    from sqlalchemy import and_, func, or_

    search_pattern = f"%{query}%"

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(
            and_(
                or_(
                    Ingredient.user_id == None,  # noqa: E711
                    Ingredient.user_id == db_user.id,
                ),
                or_(
                    Ingredient.name.ilike(search_pattern),
                    func.json_array_length(Ingredient.aliases) > 0,
                ),
            )
        )
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(50)
    )
    all_ingredients = ingredient_query_result.scalars().all()

    ingredients = []
    for ing in all_ingredients:
        if query in ing.name.lower():
            ingredients.append(ing)
            continue
        if ing.aliases:
            for alias in ing.aliases:
                if query in alias.lower():
                    ingredients.append(ing)
                    break
        if len(ingredients) >= 10:
            break

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    for ing in ingredients:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{ing.name} ({ing.category})",
                    callback_data=f"log_ing:{ing.id}",
                )
            ]
        )

    if not ingredients:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"➕ Добавить «{query}»",
                    callback_data=f"log:add_manual:{query}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="🔍 Искать еще", callback_data="log:search_product")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="log:select_product")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(FoodLogStates.selecting_product)
    await message.answer(
        f"🔍 Результаты поиска по «{query}»:\n\nНайдено: {len(ingredients)}",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("log_ing:"), StateFilter(FoodLogStates.selecting_product))
async def log_single_ingredient(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Log a single ingredient directly."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    ingredient_id = int(callback.data.split(":", 1)[1])

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = ingredient_query_result.scalar_one_or_none()

    if not ingredient:
        await callback.answer("⚠️ Продукт не найден", show_alert=True)
        return

    await state.update_data(
        dish_id=None,
        dish_name=ingredient.name,
        ingredient_ids=[ingredient.id],
    )
    await state.set_state(FoodLogStates.confirming_log)

    keyboard = build_confirm_log_keyboard()

    await message.edit_text(
        f"🥗 {ingredient.name}\n\nЗаписать?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "log:enter_manual", StateFilter(FoodLogStates.selecting_dish))
async def enter_manual_product(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter product name manually."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodLogStates.entering_manual)
    await callback.message.edit_text(
        "✏️ <b>Ручной ввод</b>\n\nВведите название продукта или блюда:\n(например: «Яблоко», «Суп домашний»)"
    )
    await callback.answer()


@router.message(StateFilter(FoodLogStates.entering_manual))
async def process_manual_product_name(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Process manually entered product name."""
    if message.text is None:
        return

    product_name = message.text.strip()

    if len(product_name) < 2:
        await message.answer("❌ Название должно содержать минимум 2 символа.")
        return

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(
            or_(Ingredient.user_id == None, Ingredient.user_id == db_user.id),  # noqa: E711
            Ingredient.name.ilike(product_name),
        )
        .limit(1)
    )
    existing_ingredient = ingredient_query_result.scalar_one_or_none()

    if existing_ingredient:
        await state.update_data(
            dish_id=None,
            dish_name=existing_ingredient.name,
            ingredient_ids=[existing_ingredient.id],
        )
        await state.set_state(FoodLogStates.confirming_log)

        keyboard = build_confirm_log_keyboard()
        await message.answer(
            f"🥗 {existing_ingredient.name}\n\nПродукт найден в базе. Записать?",
            reply_markup=keyboard,
        )
    else:
        # Product not in database - ask if should save
        await state.update_data(manual_product_name=product_name)
        await state.set_state(FoodLogStates.asking_save_product)

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Записать и сохранить в базу",
                        callback_data="log:save_and_log",
                    )
                ],
                [InlineKeyboardButton(text="📝 Только записать", callback_data="log:just_log")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="log:cancel")],
            ]
        )

        await message.answer(
            f"📝 <b>{product_name}</b>\n\nЭтот продукт не найден в базе.\nСохранить его для будущего использования?",
            reply_markup=keyboard,
        )


@router.callback_query(F.data == "log:save_and_log", StateFilter(FoodLogStates.asking_save_product))
async def save_product_and_log(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Save product to database and proceed to logging."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    product_name = data.get("manual_product_name", "")

    ingredient = Ingredient(
        name=product_name,
        category="Другое",
        user_id=db_user.id,
        aliases=[],
    )
    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)

    await state.update_data(
        dish_id=None,
        dish_name=ingredient.name,
        ingredient_ids=[ingredient.id],
    )
    await state.set_state(FoodLogStates.confirming_log)

    keyboard = build_confirm_log_keyboard()

    await message.edit_text(
        f"✅ Продукт «{product_name}» сохранён!\n\n🥗 {ingredient.name}\n\nЗаписать приём пищи?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "log:just_log", StateFilter(FoodLogStates.asking_save_product))
async def just_log_without_saving(callback: CallbackQuery, state: FSMContext) -> None:
    """Log product without saving to database."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    product_name = data.get("manual_product_name", "")

    await state.update_data(
        dish_id=None,
        dish_name=product_name,
        ingredient_ids=[],  # Empty - will use name only
        manual_only=True,
    )
    await state.set_state(FoodLogStates.selecting_time)

    from allergo_trace_bot.keyboards.food_log import build_time_selection_keyboard

    keyboard = build_time_selection_keyboard()

    await message.edit_text(
        f"🥗 {product_name}\n\n🕐 Когда вы это съели?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("log:add_manual:"), StateFilter(FoodLogStates.selecting_product))
async def add_manual_from_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Add manual product from search (when product not found)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    product_name = callback.data.split(":", 2)[2]

    await state.update_data(manual_product_name=product_name)
    await state.set_state(FoodLogStates.asking_save_product)

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Записать и сохранить в базу",
                    callback_data="log:save_and_log",
                )
            ],
            [InlineKeyboardButton(text="📝 Только записать", callback_data="log:just_log")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="log:cancel")],
        ]
    )

    await callback.message.edit_text(
        f"📝 <b>{product_name}</b>\n\nЭтот продукт не найден в базе.\nСохранить его для будущего использования?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "log:separator")
async def ignore_separator(callback: CallbackQuery) -> None:
    """Ignore clicks on separator button."""
    await callback.answer()


@router.callback_query(F.data.startswith("log_dish:"), StateFilter(FoodLogStates.selecting_dish))
async def select_dish_for_logging(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Show dish composition and ask for confirmation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    dish_id = int(callback.data.split(":", 1)[1])

    dish_query_result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = dish_query_result.scalar_one_or_none()

    if not dish:
        await callback.answer("⚠️ Блюдо не найдено", show_alert=True)
        return

    dish_query_result = await session.execute(
        select(Ingredient)
        .join(DishIngredient, DishIngredient.ingredient_id == Ingredient.id)
        .where(DishIngredient.dish_id == dish_id)
    )
    ingredients = dish_query_result.scalars().all()
    ingredient_ids = [ing.id for ing in ingredients]
    ingredient_names = [ing.name for ing in ingredients]

    await state.update_data(
        dish_id=dish_id,
        dish_name=dish.name,
        ingredient_ids=ingredient_ids,
    )
    await state.set_state(FoodLogStates.confirming_log)

    ingredients_text = ", ".join(ingredient_names)
    keyboard = build_confirm_log_keyboard()

    await message.edit_text(
        f"🍽 {dish.name}\n\n🥗 Состав: {ingredients_text}\n\nВсё верно?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:confirm", StateFilter(FoodLogStates.confirming_log))
async def proceed_to_time_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Show time selection before saving."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    if not ingredient_ids:
        await callback.answer("⚠️ Список ингредиентов пуст", show_alert=True)
        return

    await state.set_state(FoodLogStates.selecting_time)

    from allergo_trace_bot.keyboards.food_log import build_time_selection_keyboard

    keyboard = build_time_selection_keyboard()

    await message.edit_text("🕐 Когда вы это съели?\n\nВыберите время:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("log:time:"), StateFilter(FoodLogStates.selecting_time))
async def save_with_selected_time(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Save food log entry with selected time."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    data = await state.get_data()
    dish_id = data.get("dish_id")
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])
    manual_only = data.get("manual_only", False)

    time_option = callback.data.split(":", 2)[2]

    now = datetime.now(UTC)

    if time_option == "now":
        created_at = now
    elif time_option == "morning":
        created_at = now.replace(hour=8, minute=0, second=0, microsecond=0)
    elif time_option == "afternoon":
        created_at = now.replace(hour=13, minute=0, second=0, microsecond=0)
    elif time_option == "evening":
        created_at = now.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        # Custom time format: HH:MM
        try:
            hour, minute = map(int, time_option.split(":"))
            created_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, AttributeError):
            created_at = now

    # If selected time is in future (e.g., selected morning but it's already evening), move to previous day
    if created_at > now:
        from datetime import timedelta

        created_at = created_at - timedelta(days=1)

    food_log = FoodLog(
        user_id=db_user.id,
        created_at=created_at,
        dish_id=dish_id,
        ingredients_snapshot=ingredient_ids,
    )
    session.add(food_log)
    await session.commit()

    if ingredient_ids:
        ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
        ingredients = ingredient_query_result.scalars().all()
        ingredient_names = [ing.name for ing in ingredients]
        ingredients_text = ", ".join(ingredient_names)
    elif manual_only:
        # Manual entry without saving to database
        ingredients_text = dish_name
    else:
        ingredients_text = "-"

    await state.clear()

    await message.edit_text(
        f"✅ Запись сохранена!\n\n"
        f"🍽 {dish_name}\n"
        f"🥗 Ингредиенты: {ingredients_text}\n"
        f"🕐 Время: {created_at.strftime('%H:%M')}\n\n"
        "Используйте /log_food для новой записи"
    )


@router.callback_query(F.data == "log:edit", StateFilter(FoodLogStates.confirming_log))
async def edit_composition_before_logging(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Allow editing composition before logging."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    await state.set_state(FoodLogStates.editing_ingredients)

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(ingredient_query_result.scalars().all())

    keyboard = build_edit_ingredients_keyboard(ingredients)

    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    await message.edit_text(
        f"🍽 {dish_name}\n\n🥗 Состав: {ingredients_text}\n\nУдалите ненужные ингредиенты или добавьте новые:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("log:remove_ing:"), StateFilter(FoodLogStates.editing_ingredients))
async def remove_ingredient_from_log(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Remove ingredient from composition before logging."""
    if callback.message is None or callback.data is None:
        return

    ingredient_id = int(callback.data.split(":", 2)[2])

    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    if ingredient_id in ingredient_ids:
        ingredient_ids.remove(ingredient_id)
        await state.update_data(ingredient_ids=ingredient_ids)

    if not ingredient_ids:
        await callback.answer("⚠️ Нельзя удалить все ингредиенты", show_alert=True)
        # Restore the ingredient
        ingredient_ids.append(ingredient_id)
        await state.update_data(ingredient_ids=ingredient_ids)
        return

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(ingredient_query_result.scalars().all())

    keyboard = build_edit_ingredients_keyboard(ingredients)

    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return
    message = callback.message

    await message.edit_text(
        f"🍽 {dish_name}\n\n🥗 Состав: {ingredients_text}\n\nУдалите ненужные ингредиенты или добавьте новые:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:add_ingredient", StateFilter(FoodLogStates.editing_ingredients))
async def add_ingredient_to_log_prompt(callback: CallbackQuery) -> None:
    """Prompt to add ingredient (simplified - just message)."""
    if callback.message is None:
        return

    await callback.answer(
        "💡 Функция добавления ингредиентов будет реализована в следующей версии. "
        "Пока можете только удалять ингредиенты.",
        show_alert=True,
    )


@router.callback_query(F.data == "log:done_editing", StateFilter(FoodLogStates.editing_ingredients))
async def done_editing_composition(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Finish editing and show confirmation again."""
    if callback.message is None:
        return

    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    ingredient_query_result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(ingredient_query_result.scalars().all())
    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    await state.set_state(FoodLogStates.confirming_log)

    keyboard = build_confirm_log_keyboard()

    if isinstance(callback.message, InaccessibleMessage):
        return
    message = callback.message

    await message.edit_text(
        f"🍽 {dish_name}\n\n🥗 Состав: {ingredients_text}\n\nВсё верно?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:back_to_confirm", StateFilter(FoodLogStates.selecting_time))
async def back_to_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Go back to confirmation screen from time selection."""
    if callback.message is None:
        return

    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(result.scalars().all())
    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    await state.set_state(FoodLogStates.confirming_log)

    keyboard = build_confirm_log_keyboard()

    if isinstance(callback.message, InaccessibleMessage):
        return
    message = callback.message

    await message.edit_text(
        f"🍽 {dish_name}\n\n🥗 Состав: {ingredients_text}\n\nВсё верно?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:cancel", StateFilter(FoodLogStates))
async def cancel_food_logging(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel food logging."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    message = callback.message
    await message.edit_text("❌ Запись приема пищи отменена")
