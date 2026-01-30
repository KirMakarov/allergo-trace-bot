"""DishIngredient association model."""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DishIngredient(Base):
    """Association table for many-to-many relationship between dishes and ingredients."""

    __tablename__ = "dish_ingredients"

    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True
    )
