"""UserSafeIngredient model for tracking user's safe (non-allergenic) foods."""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSafeIngredient(Base):
    """Association table for user's safe ingredients (white list).

    This tracks ingredients that the user has marked as safe
    (does not trigger allergic reactions).
    Big 8 allergens cannot be added to this list.
    """

    __tablename__ = "user_safe_ingredients"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True
    )
