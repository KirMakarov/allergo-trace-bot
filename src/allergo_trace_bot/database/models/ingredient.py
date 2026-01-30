"""Ingredient model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .dish import Dish
    from .user import User


class Ingredient(Base):
    """Ingredient table with support for global and user-specific ingredients."""

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False, comment="Array of string aliases")
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="NULL = global ingredient"
    )

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="ingredients")
    dishes: Mapped[list[Dish]] = relationship("Dish", secondary="dish_ingredients", back_populates="ingredients")

    __table_args__ = (UniqueConstraint("name", "user_id", name="uq_ingredient_name_user"),)
