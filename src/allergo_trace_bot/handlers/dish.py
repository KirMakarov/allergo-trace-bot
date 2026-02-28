"""Handlers for dish creation and management."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import Dish, DishIngredient, Ingredient, User
from allergo_trace_bot.keyboards.dish import build_dish_composition_keyboard, build_dish_list_keyboard
from allergo_trace_bot.keyboards.food import (
    build_categories_keyboard,
    build_category_ingredients_keyboard,
    build_ingredient_search_results,
)

router = Router(name="dish")


class DishStates(StatesGroup):
    """States for dish creation flow."""

    waiting_for_dish_name = State()  # Waiting for dish name
    waiting_for_category = State()  # Waiting for dish category
    adding_ingredients = State()  # Adding ingredients to dish
    waiting_for_ingredient_search = State()  # Waiting for search query
    waiting_for_new_ingredient_name = State()  # Creating new ingredient during dish creation
    waiting_for_new_ingredient_category = State()  # Selecting category for new ingredient


@router.message(Command("new_dish"))
async def cmd_new_dish(message: Message, state: FSMContext) -> None:
    """Start creating a new dish."""
    await state.set_state(DishStates.waiting_for_dish_name)
    await message.answer("🍽 Create New Dish\n\nEnter dish name (e.g., 'Morning Omelette', 'Borscht'):")


@router.message(DishStates.waiting_for_dish_name)
async def process_dish_name(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process dish name and ask for category."""
    if message.text is None:
        return

    dish_name = message.text.strip()

    if len(dish_name) < 2:
        await message.answer("⚠️ Name must contain at least 2 characters. Try again:")
        return

    # Check if dish with same name already exists
    result = await session.execute(select(Dish).where(Dish.user_id == db_user.id, Dish.name == dish_name))
    existing_dish = result.scalar_one_or_none()

    if existing_dish:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Rename", callback_data="dish:rename")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="dish:cancel_early")],
            ]
        )
        await message.answer(f"⚠️ Dish with name '{dish_name}' already exists.\n\nSelect action:", reply_markup=keyboard)
        # Save the name anyway in case they want to edit
        await state.update_data(dish_name=dish_name)
        return

    # Save dish name to FSM context
    await state.update_data(dish_name=dish_name)
    await state.set_state(DishStates.waiting_for_category)

    # Show categories
    keyboard = build_categories_keyboard(action_prefix="dish_cat")
    await message.answer(f"📝 Name: {dish_name}\n\nSelect dish category:", reply_markup=keyboard)


@router.callback_query(F.data == "dish:rename", StateFilter(DishStates.waiting_for_dish_name))
async def rename_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Allow user to rename the dish."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await message.edit_text("📝 Enter new dish name:")
    # State remains waiting_for_dish_name


@router.callback_query(F.data == "dish:cancel_early", StateFilter(DishStates.waiting_for_dish_name))
async def cancel_dish_early(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel dish creation at name stage."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await state.clear()
    await message.edit_text("❌ Dish creation cancelled")


@router.callback_query(F.data.startswith("dish_cat:"), StateFilter(DishStates.waiting_for_category))
async def select_dish_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Process dish category selection and start adding ingredients."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    category = callback.data.split(":", 1)[1]

    # Save category and initialize ingredients list
    await state.update_data(dish_category=category, ingredient_ids=[])

    data = await state.get_data()
    dish_name = data.get("dish_name", "")

    await state.set_state(DishStates.adding_ingredients)

    # Show keyboard with options to add ingredients or save dish
    keyboard = build_dish_composition_keyboard(
        ingredient_ids=[],
        dish_name=dish_name,
        category=category,
    )

    await message.edit_text(
        f"🍽 Dish: {dish_name}\n📁 Category: {category}\n\n🥗 Ingredients: (empty)\n\nAdd ingredients to the dish:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "dish:add_ingredient", StateFilter(DishStates.adding_ingredients))
async def add_ingredient_to_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding ingredient to dish - show categories."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    keyboard = build_categories_keyboard(action_prefix="dish_ing_cat")

    await message.edit_text(
        "🔍 Select product category or start searching:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("dish_ing_cat:"), StateFilter(DishStates.adding_ingredients))
async def select_ingredient_category(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show ingredients from selected category."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    category = callback.data.split(":", 1)[1]

    # Get ingredients from category
    result = await session.execute(
        select(Ingredient)
        .where(Ingredient.category == category)
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(20)
    )
    ingredients = list(result.scalars().all())

    keyboard = build_category_ingredients_keyboard(ingredients, category, action_prefix="dish_select_ing")

    await message.edit_text(
        f"📁 Category: {category}\n\nSelect product:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "dish:search_ingredient", StateFilter(DishStates.adding_ingredients))
async def search_ingredient_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter search query for ingredient."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await state.set_state(DishStates.waiting_for_ingredient_search)
    await message.edit_text("🔍 Enter product name to search:\n\nFor example: milk, tomato, chicken")


@router.message(DishStates.waiting_for_ingredient_search)
async def process_ingredient_search(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Process ingredient search query."""
    if message.text is None:
        return

    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Query must contain at least 2 characters. Try again:")
        return

    # Search ingredients (including aliases)
    search_pattern = f"%{query}%"

    # Search by name OR in aliases array
    # For SQLite JSON search, we need to check if any alias matches

    result = await session.execute(
        select(Ingredient)
        .where(
            and_(
                or_(
                    Ingredient.user_id.is_(None),
                    Ingredient.user_id == db_user.id,
                ),
                or_(
                    Ingredient.name.ilike(search_pattern),
                    # Check if query exists in aliases JSON array
                    func.json_array_length(Ingredient.aliases) > 0,
                ),
            )
        )
        .order_by(Ingredient.user_id.desc(), Ingredient.name)
        .limit(50)  # Get more to filter in Python
    )
    all_ingredients = result.scalars().all()

    # Filter in Python to check aliases properly
    ingredients = []
    for ing in all_ingredients:
        # Check name match
        if query.lower() in ing.name.lower():
            ingredients.append(ing)
            continue
        # Check aliases match
        if ing.aliases:
            for alias in ing.aliases:
                if query.lower() in alias.lower():
                    ingredients.append(ing)
                    break
        if len(ingredients) >= 10:
            break

    # Save search query to state for potential use in add_custom
    await state.update_data(last_search_query=query)

    if not ingredients:
        # Show option to search again or add custom
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Search again", callback_data="dish_search_prompt")],
                [InlineKeyboardButton(text="➕ Add custom product", callback_data="add_custom")],
                [InlineKeyboardButton(text="✅ Finish adding", callback_data="dish_finish_ingredients")],
            ]
        )
        await state.set_state(DishStates.adding_ingredients)
        await message.answer(
            f"🔍 Nothing found for <b>«{query}»</b>.\n\nTry another query or add custom product.",
            reply_markup=keyboard,
        )
    else:
        keyboard = build_ingredient_search_results(
            ingredients, query, action_prefix="dish_select_ing", show_add_custom=True
        )

        await state.set_state(DishStates.adding_ingredients)
        await message.answer(f"🔍 Search results for '{query}':", reply_markup=keyboard)


@router.callback_query(F.data == "dish_search_prompt", StateFilter(DishStates.adding_ingredients))
async def dish_search_again_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to search again during dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    keyboard = build_categories_keyboard(action_prefix="dish_ing_cat")
    await state.set_state(DishStates.adding_ingredients)
    await callback.message.edit_text(
        "🔍 Select product category or start searching:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "add_custom", StateFilter(DishStates.adding_ingredients))
async def start_add_custom_ingredient_in_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding custom ingredient during dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    # Get last search query to suggest as ingredient name
    data = await state.get_data()
    last_query = data.get("last_search_query", "")

    if last_query:
        # Offer to use the search query as the name
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"✅ Use «{last_query}»", callback_data="use_search_query")],
                [InlineKeyboardButton(text="✏️ Enter another name", callback_data="enter_custom_name")],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="dish_search_prompt")],
            ]
        )
        await state.set_state(DishStates.waiting_for_new_ingredient_name)
        await message.edit_text(
            f"📝 <b>Adding new ingredient</b>\n\n"
            f"You searched for: <b>«{last_query}»</b>\n\n"
            f"Use this query as product name or enter another?",
            reply_markup=keyboard,
        )
    else:
        await state.set_state(DishStates.waiting_for_new_ingredient_name)
        await message.edit_text("📝 Adding new ingredient\n\nEnter product name (e.g.: 'Almond milk'):")


@router.callback_query(F.data == "use_search_query", StateFilter(DishStates.waiting_for_new_ingredient_name))
async def use_search_query_as_name_in_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Use last search query as ingredient name during dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    name = data.get("last_search_query", "").strip()

    if not name or len(name) < 2:
        await callback.answer("❌ Invalid name", show_alert=True)
        return

    # Save ingredient name and ask for category
    await state.update_data(new_ingredient_name=name)
    await state.set_state(DishStates.waiting_for_new_ingredient_category)

    keyboard = build_categories_keyboard(action_prefix="dish_new_ing_cat")
    await message.edit_text(
        f"📝 Product: <b>{name}</b>\n\nSelect category:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "enter_custom_name", StateFilter(DishStates.waiting_for_new_ingredient_name))
async def enter_custom_name_in_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to enter custom ingredient name during dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await state.set_state(DishStates.waiting_for_new_ingredient_name)
    await message.edit_text("📝 Adding new ingredient\n\nEnter product name (e.g.: 'Almond milk'):")
    await callback.answer()


@router.callback_query(F.data == "back_to_categories", StateFilter(DishStates.adding_ingredients))
async def back_to_categories_in_dish(callback: CallbackQuery) -> None:
    """Return to category selection when adding ingredient to dish."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    keyboard = build_categories_keyboard(action_prefix="dish_ing_cat")

    await message.edit_text(
        "🔍 Select product category or start searching:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "search_prompt", StateFilter(DishStates.adding_ingredients))
async def search_prompt_in_dish(callback: CallbackQuery, state: FSMContext) -> None:
    """Show search prompt when adding ingredient to dish."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await state.set_state(DishStates.waiting_for_ingredient_search)
    await message.edit_text("🔍 Enter product name to search:\n\nFor example: milk, tomato, chicken")


@router.callback_query(F.data.startswith("use_search_query:"), StateFilter(DishStates.waiting_for_new_ingredient_name))
async def use_search_query_as_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Use search query as new ingredient name."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    # Extract query from callback data
    ingredient_name = callback.data.split(":", 1)[1]

    # Save ingredient name and ask for category
    await state.update_data(new_ingredient_name=ingredient_name)
    await state.set_state(DishStates.waiting_for_new_ingredient_category)

    keyboard = build_categories_keyboard(action_prefix="dish_new_ing_cat")
    await message.edit_text(f"📝 Product: {ingredient_name}\n\nSelect category:", reply_markup=keyboard)


@router.callback_query(F.data == "enter_custom_name", StateFilter(DishStates.waiting_for_new_ingredient_name))
async def prompt_enter_custom_name(callback: CallbackQuery) -> None:
    """Prompt user to enter another name."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await message.edit_text("📝 Adding new ingredient\n\nEnter product name:")


@router.message(DishStates.waiting_for_new_ingredient_name)
async def process_new_ingredient_name_in_dish(message: Message, state: FSMContext) -> None:
    """Process new ingredient name during dish creation."""
    if message.text is None:
        return

    ingredient_name = message.text.strip()

    if len(ingredient_name) < 2:
        await message.answer("⚠️ Name must contain at least 2 characters. Try again:")
        return

    # Save ingredient name and ask for category
    await state.update_data(new_ingredient_name=ingredient_name)
    await state.set_state(DishStates.waiting_for_new_ingredient_category)

    keyboard = build_categories_keyboard(action_prefix="dish_new_ing_cat")
    await message.answer(f"📝 Product: {ingredient_name}\n\nSelect category:", reply_markup=keyboard)


@router.callback_query(
    F.data.startswith("dish_new_ing_cat:"), StateFilter(DishStates.waiting_for_new_ingredient_category)
)
async def save_new_ingredient_in_dish(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    """Save new ingredient and return to dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    ingredient_name = data.get("new_ingredient_name", "")

    # Check for duplicates
    result = await session.execute(
        select(Ingredient).where(Ingredient.user_id == db_user.id, Ingredient.name == ingredient_name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await callback.answer("⚠️ This product already exists", show_alert=True)
        return

    # Create ingredient
    ingredient = Ingredient(
        name=ingredient_name,
        category=category,
        user_id=db_user.id,
    )
    session.add(ingredient)
    await session.flush()  # Get ingredient.id

    # Add to dish's ingredients
    ingredient_ids: list[int] = data.get("ingredient_ids", [])
    ingredient_ids.append(ingredient.id)
    await state.update_data(ingredient_ids=ingredient_ids)

    await session.commit()

    # Get all current ingredients for display
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = result.scalars().all()
    ingredient_names = [ing.name for ing in ingredients]

    dish_name = data.get("dish_name", "")
    dish_category = data.get("dish_category", "")

    await state.set_state(DishStates.adding_ingredients)

    keyboard = build_dish_composition_keyboard(
        ingredient_ids=ingredient_ids,
        dish_name=dish_name,
        category=dish_category,
    )

    ingredients_text = ", ".join(ingredient_names)

    await message.edit_text(
        f"✅ Product '{ingredient_name}' added!\n\n"
        f"🍽 Dish: {dish_name}\n"
        f"📁 Category: {dish_category}\n\n"
        f"🥗 Ingredients ({len(ingredient_ids)}): {ingredients_text}\n\n"
        "Add more ingredients or save the dish:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("dish_select_ing:"), StateFilter(DishStates.adding_ingredients))
async def add_selected_ingredient(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Add selected ingredient to dish composition."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    ingredient_id = int(callback.data.split(":", 1)[1])

    # Get current data
    data = await state.get_data()
    ingredient_ids: list[int] = data.get("ingredient_ids", [])
    dish_name = data.get("dish_name", "")
    category = data.get("dish_category", "")

    # Check if ingredient already added
    if ingredient_id in ingredient_ids:
        await callback.answer("⚠️ This ingredient is already added", show_alert=True)
        return

    # Add ingredient to list
    ingredient_ids.append(ingredient_id)
    await state.update_data(ingredient_ids=ingredient_ids)

    # Get ingredient names
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = result.scalars().all()
    ingredient_names = [ing.name for ing in ingredients]

    # Update keyboard
    keyboard = build_dish_composition_keyboard(
        ingredient_ids=ingredient_ids,
        dish_name=dish_name,
        category=category,
    )

    ingredients_text = ", ".join(ingredient_names)

    await message.edit_text(
        f"🍽 Dish: {dish_name}\n"
        f"📁 Category: {category}\n\n"
        f"🥗 Ingredients ({len(ingredient_ids)}): {ingredients_text}\n\n"
        "Add more ingredients or save the dish:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("dish:remove_ing:"), StateFilter(DishStates.adding_ingredients))
async def remove_ingredient_from_dish(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Remove ingredient from dish composition."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    ingredient_id = int(callback.data.split(":", 2)[2])

    # Get current data
    data = await state.get_data()
    ingredient_ids: list[int] = data.get("ingredient_ids", [])
    dish_name = data.get("dish_name", "")
    category = data.get("dish_category", "")

    # Remove ingredient
    if ingredient_id in ingredient_ids:
        ingredient_ids.remove(ingredient_id)
        await state.update_data(ingredient_ids=ingredient_ids)

    # Get ingredient names
    if ingredient_ids:
        result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
        ingredients = result.scalars().all()
        ingredient_names = [ing.name for ing in ingredients]
        ingredients_text = ", ".join(ingredient_names)
    else:
        ingredients_text = "(empty)"

    # Update keyboard
    keyboard = build_dish_composition_keyboard(
        ingredient_ids=ingredient_ids,
        dish_name=dish_name,
        category=category,
    )

    await message.edit_text(
        f"🍽 Dish: {dish_name}\n"
        f"📁 Category: {category}\n\n"
        f"🥗 Ingredients ({len(ingredient_ids)}): {ingredients_text}\n\n"
        "Add ingredients or save the dish:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "dish:save", StateFilter(DishStates.adding_ingredients))
async def save_dish(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Save dish to database."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    category = data.get("dish_category", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    if not ingredient_ids:
        await callback.answer("⚠️ Add at least one ingredient", show_alert=True)
        return

    # Note: Duplicate check is now done at name input stage, so we can proceed directly
    # Create dish
    dish = Dish(
        user_id=db_user.id,
        name=dish_name,
        category=category,
    )
    session.add(dish)
    await session.flush()  # Get dish.id

    # Add ingredients to dish
    for ingredient_id in ingredient_ids:
        dish_ingredient = DishIngredient(
            dish_id=dish.id,
            ingredient_id=ingredient_id,
        )
        session.add(dish_ingredient)

    await session.commit()

    # Get ingredient names for confirmation
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = result.scalars().all()
    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    await state.clear()
    await message.edit_text(
        f"✅ Dish saved!\n\n"
        f"🍽 {dish_name}\n"
        f"📁 {category}\n"
        f"🥗 Ingredients: {ingredients_text}\n\n"
        f"Use /log_food to log a meal"
    )


@router.callback_query(F.data == "dish:cancel", StateFilter(DishStates.adding_ingredients))
async def cancel_dish_creation(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel dish creation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    message = callback.message
    await state.clear()
    await message.edit_text("❌ Dish creation cancelled")


@router.message(Command("my_dishes"))
async def cmd_my_dishes(message: Message, session: AsyncSession, db_user: User) -> None:
    """Show user's dishes."""
    # Get user's dishes
    result = await session.execute(select(Dish).where(Dish.user_id == db_user.id).order_by(Dish.category, Dish.name))
    dishes = list(result.scalars().all())

    if not dishes:
        await message.answer("📝 You have no saved dishes yet\n\nUse /new_dish to create your first dish")
        return

    keyboard = build_dish_list_keyboard(dishes, action_prefix="view_dish")

    await message.answer(
        f"🍽 Your dishes ({len(dishes)}):\n\nSelect a dish to view:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("view_dish:"))
async def view_dish_details(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show dish details with ingredients."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    dish_id = int(callback.data.split(":", 1)[1])

    # Get dish with ingredients
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()

    if not dish:
        await callback.answer("⚠️ Dish not found", show_alert=True)
        return

    # Get ingredients
    result = await session.execute(
        select(Ingredient)
        .join(DishIngredient, DishIngredient.ingredient_id == Ingredient.id)
        .where(DishIngredient.dish_id == dish_id)
    )
    ingredients = result.scalars().all()
    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

    await message.edit_text(
        f"🍽 {dish.name}\n"
        f"📁 {dish.category}\n\n"
        f"🥗 Ingredients ({len(ingredients)}):\n{ingredients_text}\n\n"
        "Use /log_food to log a meal"
    )
