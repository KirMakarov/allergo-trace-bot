"""FoodLog model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .dish import Dish
    from .user import User


class FoodLog(Base):
    """Food consumption log with ingredient snapshots."""

    __tablename__ = "food_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
        comment="Stored in UTC",
    )
    dish_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("dishes.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to template dish if used",
    )
    ingredients_snapshot: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, comment="Array of ingredient IDs actually consumed"
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="food_logs")
    dish: Mapped[Dish | None] = relationship("Dish", back_populates="food_logs")
