"""Dish model."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .food_log import FoodLog
    from .ingredient import Ingredient
    from .user import User


class Dish(Base):
    """Dish templates created by users."""

    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="dishes")
    ingredients: Mapped[list[Ingredient]] = relationship(
        "Ingredient", secondary="dish_ingredients", back_populates="dishes"
    )
    food_logs: Mapped[list[FoodLog]] = relationship("FoodLog", back_populates="dish")
