"""Analytics service for correlation analysis between food and symptoms.

This module implements the core algorithm for finding correlations between
consumed ingredients and reported symptoms, with special handling for
Big 8 allergens.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import (
    Dish,
    FoodLog,
    Ingredient,
    SymptomLog,
    UserSafeIngredient,
)


@dataclass
class IngredientOccurrence:
    """Tracks ingredient occurrences with dish context."""

    ingredient_id: int
    ingredient_name: str
    is_big8: bool
    dish_names: list[str] = field(default_factory=list)
    symptom_count: int = 0
    total_count: int = 0

    @property
    def risk_score(self) -> float:
        """Calculate risk score as percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.symptom_count / self.total_count) * 100

    @property
    def dish_context(self) -> str:
        """Get formatted dish context for reporting."""
        if not self.dish_names:
            return ""
        unique_dishes = list(set(self.dish_names))
        if len(unique_dishes) == 1:
            return f"в составе '{unique_dishes[0]}'"
        dishes_formatted = ", ".join(f"'{d}'" for d in unique_dishes[:3])
        return f"в блюдах: {dishes_formatted}"


@dataclass
class AnalyticsReport:
    """Container for analytics report data."""

    big8_allergens: list[IngredientOccurrence] = field(default_factory=list)
    high_risk: list[IngredientOccurrence] = field(default_factory=list)  # >50%
    low_risk: list[IngredientOccurrence] = field(default_factory=list)  # <=50%
    safe_candidates: list[IngredientOccurrence] = field(default_factory=list)  # <10%
    time_window_hours: int = 6
    symptoms_analyzed: int = 0
    food_logs_analyzed: int = 0

    def has_data(self) -> bool:
        """Check if report has any meaningful data."""
        return bool(self.big8_allergens or self.high_risk or self.low_risk)


class AnalyticsService:
    """Service for analyzing food-symptom correlations."""

    # Minimum severity level to consider symptom as significant
    MIN_SYMPTOM_SEVERITY = 3

    def __init__(self, session: AsyncSession) -> None:
        """Initialize analytics service.

        Args:
            session: Database session for queries
        """
        self.session = session

    async def get_user_safe_ingredients(self, user_id: int) -> set[int]:
        """Get set of ingredient IDs marked as safe by user.

        Args:
            user_id: Telegram user ID

        Returns:
            Set of safe ingredient IDs
        """
        result = await self.session.execute(
            select(UserSafeIngredient.ingredient_id).where(UserSafeIngredient.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get_ingredient_info(self, ingredient_ids: set[int]) -> dict[int, tuple[str, bool]]:
        """Get ingredient names and Big 8 status.

        Args:
            ingredient_ids: Set of ingredient IDs to look up

        Returns:
            Dict mapping ingredient_id -> (name, is_big8)
        """
        if not ingredient_ids:
            return {}

        result = await self.session.execute(
            select(Ingredient.id, Ingredient.name, Ingredient.is_big8).where(Ingredient.id.in_(ingredient_ids))
        )
        return {row.id: (row.name, row.is_big8) for row in result}

    async def get_dish_name(self, dish_id: int | None) -> str | None:
        """Get dish name by ID.

        Args:
            dish_id: Dish ID or None

        Returns:
            Dish name or None
        """
        if dish_id is None:
            return None

        result = await self.session.execute(select(Dish.name).where(Dish.id == dish_id))
        row = result.scalar_one_or_none()
        return row if row else None

    async def analyze_correlations(self, user_id: int, time_window_hours: int) -> AnalyticsReport:
        """Analyze correlations between food and symptoms.

        Algorithm:
        1. Find all significant symptoms (severity >= 3)
        2. For each symptom, find food logs within time window
        3. Unpack ingredients from food logs, tracking dish context
        4. Filter out safe ingredients (unless Big 8)
        5. Calculate risk scores

        Args:
            user_id: Telegram user ID
            time_window_hours: How many hours before symptom to look for food

        Returns:
            AnalyticsReport with categorized results
        """
        report = AnalyticsReport(time_window_hours=time_window_hours)

        # Get user's safe ingredients
        safe_ids = await self.get_user_safe_ingredients(user_id)

        # Get all significant symptoms
        symptoms_result = await self.session.execute(
            select(SymptomLog).where(
                SymptomLog.user_id == user_id,
                SymptomLog.severity >= self.MIN_SYMPTOM_SEVERITY,
            )
        )
        symptoms = symptoms_result.scalars().all()
        report.symptoms_analyzed = len(symptoms)

        if not symptoms:
            return report

        # Track ingredients before symptoms
        # ingredient_id -> IngredientOccurrence
        before_symptom: dict[int, IngredientOccurrence] = {}

        # Get all food logs for the user (for total count calculation)
        all_food_result = await self.session.execute(select(FoodLog).where(FoodLog.user_id == user_id))
        all_food_logs = all_food_result.scalars().all()
        report.food_logs_analyzed = len(all_food_logs)

        # Build map of all ingredient occurrences (total count)
        all_ingredients: dict[int, int] = defaultdict(int)
        all_dish_contexts: dict[int, list[str]] = defaultdict(list)

        for food_log in all_food_logs:
            dish_name = await self.get_dish_name(food_log.dish_id)
            for ing_id in food_log.ingredients_snapshot or []:
                all_ingredients[ing_id] += 1
                if dish_name:
                    all_dish_contexts[ing_id].append(dish_name)

        # For each symptom, find food eaten before it
        for symptom in symptoms:
            window_start = symptom.created_at - timedelta(hours=time_window_hours)

            # Find food logs in the time window
            food_result = await self.session.execute(
                select(FoodLog).where(
                    FoodLog.user_id == user_id,
                    FoodLog.created_at >= window_start,
                    FoodLog.created_at <= symptom.created_at,
                )
            )
            food_logs = food_result.scalars().all()

            # Unpack ingredients with dish context
            for food_log in food_logs:
                dish_name = await self.get_dish_name(food_log.dish_id)
                for ing_id in food_log.ingredients_snapshot or []:
                    if ing_id not in before_symptom:
                        before_symptom[ing_id] = IngredientOccurrence(
                            ingredient_id=ing_id,
                            ingredient_name="",  # Will be filled later
                            is_big8=False,
                        )
                    before_symptom[ing_id].symptom_count += 1
                    if dish_name:
                        before_symptom[ing_id].dish_names.append(dish_name)

        # Get ingredient info
        all_ing_ids = set(before_symptom.keys()) | set(all_ingredients.keys())
        ingredient_info = await self.get_ingredient_info(all_ing_ids)

        # Fill in ingredient details and apply filtering
        for ing_id, occurrence in before_symptom.items():
            if ing_id in ingredient_info:
                name, is_big8 = ingredient_info[ing_id]
                occurrence.ingredient_name = name
                occurrence.is_big8 = is_big8
            occurrence.total_count = all_ingredients.get(ing_id, 0)
            occurrence.dish_names = all_dish_contexts.get(ing_id, [])[:5]

            # Apply safety filter (Big 8 always analyzed)
            if ing_id in safe_ids and not occurrence.is_big8:
                continue

            # Categorize by risk
            if occurrence.is_big8:
                report.big8_allergens.append(occurrence)
            elif occurrence.risk_score > 50:
                report.high_risk.append(occurrence)
            else:
                report.low_risk.append(occurrence)

        # Find safe candidates (ingredients with low risk score, not Big 8)
        for ing_id, total_count in all_ingredients.items():
            if ing_id in ingredient_info:
                name, is_big8 = ingredient_info[ing_id]
                if is_big8 or ing_id in safe_ids:
                    continue

                symptom_count = before_symptom[ing_id].symptom_count if ing_id in before_symptom else 0
                risk_score = (symptom_count / total_count) * 100 if total_count > 0 else 0

                # Low risk but consumed at least once
                if 0 < risk_score < 10 and total_count >= 2:
                    occurrence = IngredientOccurrence(
                        ingredient_id=ing_id,
                        ingredient_name=name,
                        is_big8=False,
                        symptom_count=symptom_count,
                        total_count=total_count,
                    )
                    report.safe_candidates.append(occurrence)

        # Sort by risk score (descending)
        report.big8_allergens.sort(key=lambda x: x.risk_score, reverse=True)
        report.high_risk.sort(key=lambda x: x.risk_score, reverse=True)
        report.low_risk.sort(key=lambda x: x.risk_score, reverse=True)
        report.safe_candidates.sort(key=lambda x: x.risk_score)

        return report

    async def add_safe_ingredients(self, user_id: int, ingredient_ids: list[int]) -> int:
        """Add ingredients to user's safe list.

        Note: Big 8 allergens cannot be added as safe.

        Args:
            user_id: Telegram user ID
            ingredient_ids: List of ingredient IDs to mark as safe

        Returns:
            Number of ingredients actually added
        """
        if not ingredient_ids:
            return 0

        # Filter out Big 8 allergens
        result = await self.session.execute(
            select(Ingredient.id).where(
                Ingredient.id.in_(ingredient_ids),
                Ingredient.is_big8.is_(False),
            )
        )
        safe_ids = set(result.scalars().all())

        # Get existing safe ingredients
        existing_result = await self.session.execute(
            select(UserSafeIngredient.ingredient_id).where(
                UserSafeIngredient.user_id == user_id,
                UserSafeIngredient.ingredient_id.in_(safe_ids),
            )
        )
        existing = set(existing_result.scalars().all())

        # Add new safe ingredients
        added = 0
        for ing_id in safe_ids - existing:
            self.session.add(UserSafeIngredient(user_id=user_id, ingredient_id=ing_id))
            added += 1

        await self.session.commit()
        return added

    async def get_safe_candidates_for_selection(
        self, user_id: int, time_window_hours: int = 24
    ) -> list[IngredientOccurrence]:
        """Get list of ingredients that could be marked as safe.

        Criteria:
        - Risk score < 10% (rarely correlated with symptoms)
        - Consumed at least 2 times
        - NOT Big 8 allergen
        - NOT already in safe list

        Args:
            user_id: Telegram user ID
            time_window_hours: Time window for analysis

        Returns:
            List of candidate ingredients
        """
        report = await self.analyze_correlations(user_id, time_window_hours)
        safe_ids = await self.get_user_safe_ingredients(user_id)

        candidates = [occ for occ in report.safe_candidates if occ.ingredient_id not in safe_ids and not occ.is_big8]

        return candidates[:15]  # Limit to 15 for UI


def format_analytics_report(report: AnalyticsReport) -> str:
    """Format analytics report as user-friendly message.

    Args:
        report: Analytics report to format

    Returns:
        Formatted message string with Telegram HTML markup
    """
    if not report.has_data():
        return (
            "📊 <b>Анализ корреляций</b>\n\n"
            f"⏱ Временное окно: {report.time_window_hours} часов\n\n"
            "ℹ️ <i>Недостаточно данных для анализа.</i>\n\n"
            "Для анализа нужны:\n"
            "• Записи о еде (/log_food)\n"
            "• Записи симптомов с оценкой ≥3"
        )

    lines = [
        "📊 <b>Анализ корреляций еды и симптомов</b>",
        f"⏱ Временное окно: {report.time_window_hours} ч.\n",
    ]

    # Block 1: Big 8 Allergens (Priority)
    if report.big8_allergens:
        lines.append('⚠️ <b>Внимание! Аллергены "Большой Восьмерки":</b>')
        for occ in report.big8_allergens[:5]:
            context = f" ({occ.dish_context})" if occ.dish_context else ""
            lines.append(
                f"— <b>{occ.ingredient_name}</b>{context}: "
                f"{occ.symptom_count} из {occ.total_count} раз "
                f"({occ.risk_score:.0f}%)"
            )
        lines.append("")

    # Block 2: High Risk (>50%)
    if report.high_risk:
        lines.append("🔴 <b>Подозрение (высокая вероятность):</b>")
        for occ in report.high_risk[:5]:
            context = f" ({occ.dish_context})" if occ.dish_context else ""
            lines.append(
                f"— <b>{occ.ingredient_name}</b>{context}: "
                f"{occ.risk_score:.0f}% ({occ.symptom_count}/{occ.total_count})"
            )
        lines.append("")

    # Block 3: Low Risk
    if report.low_risk:
        lines.append("🟡 <b>Низкая вероятность:</b>")
        for occ in report.low_risk[:5]:
            lines.append(f"— {occ.ingredient_name}: {occ.risk_score:.0f}% ({occ.symptom_count}/{occ.total_count})")
        lines.append("")

    # Summary
    lines.append(
        f"<i>Проанализировано: {report.symptoms_analyzed} симптомов, {report.food_logs_analyzed} записей о еде</i>"
    )

    return "\n".join(lines)
