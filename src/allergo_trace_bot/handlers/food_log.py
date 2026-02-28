"""Handlers for food logging (recording meals)."""

from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import Dish, DishIngredient, FoodLog, Ingredient, User
from allergo_trace_bot.keyboards.food import build_categories_keyboard, build_category_ingredients_keyboard
from allergo_trace_bot.keyboards.food_log import (
    build_confirm_log_keyboard,
    build_dish_selection_keyboard,
    build_edit_ingredients_keyboard,
    build_time_selection_keyboard,
)
from allergo_trace_bot.utils.datetime_utils import get_utc_now

router = Router(name="food_log")


class FoodLogStates(StatesGroup):
    """States for food logging flow."""

    selecting_dish = State()  # Selecting dish to log
    confirming_log = State()  # Confirming or editing composition
    editing_ingredients = State()  # Editing ingredients before logging
    selecting_time = State()  # Selecting time for the meal
    selecting_product = State()  # Selecting product from database
    searching_product = State()  # Searching product by name
    searching_in_category = State()  # Searching product in specific category
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
        "🍽 What did you eat?\n\n"
        "Select recording method:\n"
        "• <b>Log Food Item</b> - select from database\n"
        "• <b>Enter Manually</b> - any product\n"
        "• <b>Prepared Dishes</b> - your saved dishes",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:select_product", StateFilter(FoodLogStates.selecting_dish))
async def select_product_for_logging(callback: CallbackQuery, state: FSMContext) -> None:
    """Show product categories for selection."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message

    keyboard = build_categories_keyboard(action_prefix="log_cat", show_custom_category=False)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="log:back_to_main")])

    await state.set_state(FoodLogStates.selecting_product)
    await message.edit_text(
        "🥗 <b>Select Product Category</b>\n\nOr use search:",
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
        "🍽 What did you eat?\n\n"
        "Select recording method:\n"
        "• <b>Log Food Item</b> - select from database\n"
        "• <b>Enter Manually</b> - any product\n"
        "• <b>Prepared Dishes</b> - your saved dishes",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "log:select_product", StateFilter(FoodLogStates.selecting_product))
async def back_to_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to category selection from product list."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message

    keyboard = build_categories_keyboard(action_prefix="log_cat", show_custom_category=False)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="log:back_to_main")])

    await message.edit_text(
        "🥗 <b>Select Product Category</b>\n\nOr use search:",
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

    category_ingredients_query = await session.execute(
        select(Ingredient)
        .where(Ingredient.category == category)
        .where(or_(Ingredient.user_id.is_(None), Ingredient.user_id == db_user.id))
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(20)
    )
    ingredients = list(category_ingredients_query.scalars().all())

    # Save category to state for search
    await state.update_data(current_category=category)

    keyboard = build_category_ingredients_keyboard(
        ingredients,
        category,
        action_prefix="log_ing",
        search_callback=f"log:search_in_cat:{category}",
        back_callback="log:select_product",
    )

    await message.edit_text(
        f"📁 <b>{category}</b>\n\nSelect a product:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("log:search_in_cat:"),
    StateFilter(FoodLogStates.selecting_product),
)
async def search_in_category_prompt_log(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt to search for product in specific category."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    category = callback.data.split(":", 2)[2]

    await state.update_data(current_category=category)
    await state.set_state(FoodLogStates.searching_in_category)

    await callback.message.edit_text(f"🔍 <b>Search in category: {category}</b>\n\nEnter product name to search:")
    await callback.answer()


@router.callback_query(F.data == "search_prompt", StateFilter(FoodLogStates.selecting_product))
async def search_product_prompt_log(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt to search for product."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodLogStates.searching_product)
    await callback.message.edit_text("🔍 Enter product name to search:")
    await callback.answer()


@router.callback_query(F.data == "log:search_product", StateFilter(FoodLogStates.selecting_product))
async def search_product_prompt_log_alt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt to search for product (alternative callback)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(FoodLogStates.searching_product)
    await callback.message.edit_text("🔍 Enter product name to search:")
    await callback.answer()


@router.message(StateFilter(FoodLogStates.searching_product))
async def process_product_search(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process product search query."""
    if message.text is None:
        return

    query = message.text.strip().lower()

    if len(query) < 2:
        await message.answer("❌ Enter at least 2 characters for search.")
        return

    search_pattern = f"%{query}%"

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(
            and_(
                or_(
                    Ingredient.user_id.is_(None),
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
                    text=f"➕ Add «{query}»",
                    callback_data=f"log:add_manual:{query}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="🔍 Search more", callback_data="log:search_product")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="log:select_product")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(FoodLogStates.selecting_product)
    await message.answer(
        f"🔍 Search results for «{query}»:\n\nFound: {len(ingredients)}",
        reply_markup=keyboard,
    )


@router.message(StateFilter(FoodLogStates.searching_in_category))
async def process_search_in_category_log(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Process product search query within specific category."""
    if message.text is None:
        return

    query = message.text.strip().lower()

    if len(query) < 2:
        await message.answer("❌ Enter at least 2 characters for search.")
        return

    data = await state.get_data()
    category = data.get("current_category")

    if not category:
        await message.answer("❌ Error: category not found")
        await state.set_state(FoodLogStates.selecting_product)
        return

    search_pattern = f"%{query}%"

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(Ingredient.category == category)
        .where(
            and_(
                or_(
                    Ingredient.user_id.is_(None),
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
                    text=f"➕ Add «{query}»",
                    callback_data=f"log:add_manual:{query}",
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔍 Search more in category",
                    callback_data=f"log:search_in_cat:{category}",
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔍 Search in all categories",
                    callback_data="log:search_product",
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔍 Search more in category",
                    callback_data=f"log:search_in_cat:{category}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="⬅️ Back to Category", callback_data=f"log_cat:{category}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(FoodLogStates.selecting_product)
    await message.answer(
        f"🔍 Search results in category <b>{category}</b> for «{query}»:\n\nFound: {len(ingredients)}",
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
        await callback.answer("⚠️ Product not found", show_alert=True)
        return

    await state.update_data(
        dish_id=None,
        dish_name=ingredient.name,
        ingredient_ids=[ingredient.id],
    )
    await state.set_state(FoodLogStates.confirming_log)

    keyboard = build_confirm_log_keyboard()

    await message.edit_text(
        f"🥗 {ingredient.name}\n\nLog this?",
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
        "✏️ <b>Manual Entry</b>\n\nEnter product or dish name:\n(e.g.: «Apple», «Homemade Soup»)"
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
        await message.answer("❌ Name must contain at least 2 characters.")
        return

    ingredient_query_result = await session.execute(
        select(Ingredient)
        .where(
            or_(Ingredient.user_id.is_(None), Ingredient.user_id == db_user.id),
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
            f"🥗 {existing_ingredient.name}\n\nProduct found in database. Log it?",
            reply_markup=keyboard,
        )
    else:
        # Product not in database - ask if should save
        await state.update_data(manual_product_name=product_name)
        await state.set_state(FoodLogStates.asking_save_product)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Log and Save to DB",
                        callback_data="log:save_and_log",
                    )
                ],
                [InlineKeyboardButton(text="📝 Log Only", callback_data="log:just_log")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="log:cancel")],
            ]
        )

        await message.answer(
            f"📝 <b>{product_name}</b>\n\nProduct not found in database.\nSave it for future use?",
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
        category="Other",
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
        f"✅ Product «{product_name}» saved!\n\n🥗 {ingredient.name}\n\nLog this meal?",
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

    keyboard = build_time_selection_keyboard()

    await message.edit_text(
        f"🥗 {product_name}\n\n🕐 When did you eat this?",
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Log and Save to DB",
                    callback_data="log:save_and_log",
                )
            ],
            [InlineKeyboardButton(text="📝 Log Only", callback_data="log:just_log")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="log:cancel")],
        ]
    )

    await callback.message.edit_text(
        f"📝 <b>{product_name}</b>\n\nProduct not found in database.\nSave it for future use?",
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
        await callback.answer("⚠️ Dish not found", show_alert=True)
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
        f"🍽 {dish.name}\n\n🥗 Composition: {ingredients_text}\n\nIs this correct?",
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
        await callback.answer("⚠️ Ingredient list is empty", show_alert=True)
        return

    await state.set_state(FoodLogStates.selecting_time)

    keyboard = build_time_selection_keyboard()

    await message.edit_text("🕐 When did you eat this?\n\nSelect time:", reply_markup=keyboard)


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

    now = get_utc_now()

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
        f"✅ Entry saved!\n\n"
        f"🍽 {dish_name}\n"
        f"🥗 Ingredients: {ingredients_text}\n"
        f"🕐 Time: {created_at.strftime('%H:%M')}\n\n"
        "Use /log_food for new entry"
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
        f"🍽 {dish_name}\n\n🥗 Composition: {ingredients_text}\n\nRemove unnecessary ingredients or add new ones:",
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
        await callback.answer("⚠️ Cannot remove all ingredients", show_alert=True)
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
        f"🍽 {dish_name}\n\n🥗 Composition: {ingredients_text}\n\nRemove unnecessary ingredients or add new ones:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:add_ingredient", StateFilter(FoodLogStates.editing_ingredients))
async def add_ingredient_to_log_prompt(callback: CallbackQuery) -> None:
    """Prompt to add ingredient (simplified - just message)."""
    if callback.message is None:
        return

    await callback.answer(
        "💡 Ingredient addition feature will be implemented in the next version. "
        "You can only remove ingredients for now.",
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
        f"🍽 {dish_name}\n\n🥗 Composition: {ingredients_text}\n\nIs this correct?",
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
        f"🍽 {dish_name}\n\n🥗 Composition: {ingredients_text}\n\nIs this correct?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "log:cancel", StateFilter(FoodLogStates))
async def cancel_food_logging(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel food logging."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    message = callback.message
    await message.edit_text("❌ Meal logging cancelled")
