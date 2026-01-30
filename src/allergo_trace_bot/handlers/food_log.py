"""Handlers for food logging (recording meals)."""

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import Dish, DishIngredient, FoodLog, Ingredient, User
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


@router.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext, session: AsyncSession, db_user: User) -> None:
    """Start food logging - show dish selection."""
    # Get user's dishes
    result = await session.execute(select(Dish).where(Dish.user_id == db_user.id).order_by(Dish.category, Dish.name))
    dishes = list(result.scalars().all())

    if not dishes:
        await message.answer("📝 У вас пока нет сохраненных блюд\n\nИспользуйте /new_dish чтобы создать первое блюдо")
        return

    await state.set_state(FoodLogStates.selecting_dish)

    keyboard = build_dish_selection_keyboard(dishes)

    await message.answer(
        "🍽 Что вы съели?\n\nВыберите блюдо из списка:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("log_dish:"), StateFilter(FoodLogStates.selecting_dish))
async def select_dish_for_logging(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Show dish composition and ask for confirmation."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    message = callback.message
    dish_id = int(callback.data.split(":", 1)[1])

    # Get dish
    result = await session.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()

    if not dish:
        await callback.answer("⚠️ Блюдо не найдено", show_alert=True)
        return

    # Get ingredients
    result = await session.execute(
        select(Ingredient)
        .join(DishIngredient, DishIngredient.ingredient_id == Ingredient.id)
        .where(DishIngredient.dish_id == dish_id)
    )
    ingredients = result.scalars().all()
    ingredient_ids = [ing.id for ing in ingredients]
    ingredient_names = [ing.name for ing in ingredients]

    # Save to state
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

    # Parse time from callback
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

    # Create food log entry
    food_log = FoodLog(
        user_id=db_user.id,
        created_at=created_at,
        dish_id=dish_id,
        ingredients_snapshot=ingredient_ids,
    )
    session.add(food_log)
    await session.commit()

    # Get ingredient names for confirmation
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = result.scalars().all()
    ingredient_names = [ing.name for ing in ingredients]
    ingredients_text = ", ".join(ingredient_names)

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

    # Get ingredient details
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(result.scalars().all())

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

    # Remove ingredient
    if ingredient_id in ingredient_ids:
        ingredient_ids.remove(ingredient_id)
        await state.update_data(ingredient_ids=ingredient_ids)

    if not ingredient_ids:
        await callback.answer("⚠️ Нельзя удалить все ингредиенты", show_alert=True)
        # Restore the ingredient
        ingredient_ids.append(ingredient_id)
        await state.update_data(ingredient_ids=ingredient_ids)
        return

    # Get updated ingredient details
    result = await session.execute(select(Ingredient).where(Ingredient.id.in_(ingredient_ids)))
    ingredients = list(result.scalars().all())

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

    # Get ingredient names
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


@router.callback_query(F.data == "log:back_to_confirm", StateFilter(FoodLogStates.selecting_time))
async def back_to_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Go back to confirmation screen from time selection."""
    if callback.message is None:
        return

    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    ingredient_ids: list[int] = data.get("ingredient_ids", [])

    # Get ingredient names
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
