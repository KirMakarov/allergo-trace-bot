"""Handlers for analytics commands and interactions."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import User
from allergo_trace_bot.keyboards.analytics import (
    build_no_safe_candidates_keyboard,
    build_report_actions_keyboard,
    build_safe_ingredients_selection_keyboard,
    build_time_window_keyboard,
)
from allergo_trace_bot.services.analytics import (
    AnalyticsService,
    format_analytics_report,
)

router = Router(name="analytics")


class AnalyticsStates(StatesGroup):
    """States for analytics flow."""

    choosing_window = State()  # Selecting time window for analysis
    viewing_report = State()  # Viewing analysis report
    selecting_safe = State()  # Selecting safe ingredients


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    """Handle /analyze command - start analytics flow."""
    await state.set_state(AnalyticsStates.choosing_window)

    await message.answer(
        "📊 <b>Анализ корреляций еды и симптомов</b>\n\n"
        "За какой период искать связь между едой и симптомами?\n"
        "<i>(Сколько времени обычно проходит от еды до реакции?)</i>",
        reply_markup=build_time_window_keyboard(),
    )


@router.callback_query(F.data == "analyze:cancel")
async def cancel_analysis(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel analysis flow."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    await callback.message.edit_text("❌ Анализ отменён.\n\nИспользуйте /analyze для запуска нового анализа.")
    await callback.answer()


@router.callback_query(F.data == "analyze:rerun")
async def rerun_analysis(callback: CallbackQuery, state: FSMContext) -> None:
    """Restart analysis with new time window selection."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(AnalyticsStates.choosing_window)
    await callback.message.edit_text(
        "📊 <b>Анализ корреляций еды и симптомов</b>\n\n"
        "За какой период искать связь между едой и симптомами?\n"
        "<i>(Сколько времени обычно проходит от еды до реакции?)</i>",
        reply_markup=build_time_window_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("analyze:window:"),
    StateFilter(AnalyticsStates.choosing_window),
)
async def process_time_window(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
) -> None:
    """Process time window selection and run analysis."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    try:
        time_window_hours = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("⚠️ Ошибка: неверные данные", show_alert=True)
        return

    await callback.answer("🔄 Анализирую данные...")

    service = AnalyticsService(session)
    report = await service.analyze_correlations(db_user.id, time_window_hours)

    report_text = format_analytics_report(report)

    # Store time window in state for potential rerun
    await state.update_data(time_window_hours=time_window_hours)
    await state.set_state(AnalyticsStates.viewing_report)

    keyboard = build_report_actions_keyboard() if report.has_data() else None

    await callback.message.edit_text(report_text, reply_markup=keyboard)


@router.callback_query(
    F.data == "analyze:safe:show",
    StateFilter(AnalyticsStates.viewing_report),
)
async def show_safe_selection(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
) -> None:
    """Show safe ingredients selection interface."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await callback.answer("🔄 Загружаю список...")

    data = await state.get_data()
    time_window_hours = data.get("time_window_hours", 24)

    service = AnalyticsService(session)
    candidates = await service.get_safe_candidates_for_selection(db_user.id, time_window_hours)

    if not candidates:
        await callback.message.edit_text(
            "🛡 <b>Белый список продуктов</b>\n\n"
            "ℹ️ <i>Нет подходящих продуктов для добавления в белый список.</i>\n\n"
            "Продукты попадают в список кандидатов, если:\n"
            "• Употреблялись минимум 2 раза\n"
            "• Редко совпадали с симптомами (<10%)\n"
            '• Не являются аллергенами "Большой Восьмёрки"',
            reply_markup=build_no_safe_candidates_keyboard(),
        )
        return

    await state.update_data(
        safe_candidates=[
            {
                "id": c.ingredient_id,
                "name": c.ingredient_name,
                "risk_score": c.risk_score,
            }
            for c in candidates
        ],
        selected_safe_ids=[],
    )
    await state.set_state(AnalyticsStates.selecting_safe)

    await callback.message.edit_text(
        "🛡 <b>Белый список продуктов</b>\n\n"
        "Выберите продукты, которые точно безопасны для вас.\n"
        "Они будут исключены из будущих отчётов.\n\n"
        '<i>⚠️ Аллергены "Большой Восьмёрки" не отображаются '
        "(их нельзя добавить в белый список).</i>",
        reply_markup=build_safe_ingredients_selection_keyboard(candidates, set()),
    )


@router.callback_query(
    F.data.startswith("analyze:safe:toggle:"),
    StateFilter(AnalyticsStates.selecting_safe),
)
async def toggle_safe_ingredient(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Toggle ingredient selection in safe list."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage) or callback.data is None:
        return

    # Parse ingredient ID
    try:
        ingredient_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    data = await state.get_data()
    selected_ids: list[int] = data.get("selected_safe_ids", [])
    candidates_data: list[dict[str, int | str | float]] = data.get("safe_candidates", [])

    if ingredient_id in selected_ids:
        selected_ids.remove(ingredient_id)
    else:
        selected_ids.append(ingredient_id)

    await state.update_data(selected_safe_ids=selected_ids)

    from allergo_trace_bot.services.analytics import IngredientOccurrence

    candidates = []
    for c in candidates_data:
        # Calculate symptom_count and total_count from risk_score
        # We stored risk_score = (symptom_count / total_count) * 100
        # For display purposes, we'll use symptom_count=risk_score, total_count=100
        risk = float(c.get("risk_score", 0))
        occ = IngredientOccurrence(
            ingredient_id=int(c["id"]),
            ingredient_name=str(c["name"]),
            is_big8=False,
            symptom_count=int(risk),  # Use risk as percentage
            total_count=100,  # Denominator for percentage
        )
        candidates.append(occ)

    await callback.message.edit_reply_markup(
        reply_markup=build_safe_ingredients_selection_keyboard(candidates, set(selected_ids))
    )
    await callback.answer()


@router.callback_query(
    F.data == "analyze:safe:save",
    StateFilter(AnalyticsStates.selecting_safe),
)
async def save_safe_ingredients(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
) -> None:
    """Save selected safe ingredients."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    data = await state.get_data()
    selected_ids: list[int] = data.get("selected_safe_ids", [])

    if not selected_ids:
        await callback.answer(
            "ℹ️ Ничего не выбрано. Выберите продукты или нажмите Отмена.",
            show_alert=True,
        )
        return

    service = AnalyticsService(session)
    added_count = await service.add_safe_ingredients(db_user.id, selected_ids)

    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Готово!</b>\n\n"
        f"Добавлено продуктов в белый список: {added_count}\n\n"
        "Эти продукты больше не будут засорять отчёт "
        '(кроме явных аллергенов "Большой Восьмёрки").\n\n'
        "Используйте /analyze для нового анализа."
    )
    await callback.answer("✅ Сохранено!")


@router.callback_query(
    F.data == "analyze:safe:cancel",
    StateFilter(AnalyticsStates.selecting_safe),
)
async def cancel_safe_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel safe ingredients selection."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    await callback.message.edit_text("❌ Выбор отменён.\n\nИспользуйте /analyze для нового анализа.")
    await callback.answer()
