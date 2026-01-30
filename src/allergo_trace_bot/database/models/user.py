"""User model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .dish import Dish
    from .food_log import FoodLog
    from .ingredient import Ingredient
    from .symptom_log import SymptomLog


class User(Base):
    """User table storing Telegram users and their settings."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="Telegram User ID")
    timezone: Mapped[str] = mapped_column(String, default="UTC", nullable=False)
    settings: Mapped[dict[str, list[str]]] = mapped_column(
        JSON,
        default=lambda: {"food_reminders": ["09:30", "14:00", "20:00"], "symptom_reminders": ["09:00", "21:00"]},
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    ingredients: Mapped[list[Ingredient]] = relationship(
        "Ingredient", back_populates="user", cascade="all, delete-orphan"
    )
    dishes: Mapped[list[Dish]] = relationship("Dish", back_populates="user", cascade="all, delete-orphan")
    food_logs: Mapped[list[FoodLog]] = relationship("FoodLog", back_populates="user", cascade="all, delete-orphan")
    symptom_logs: Mapped[list[SymptomLog]] = relationship(
        "SymptomLog", back_populates="user", cascade="all, delete-orphan"
    )
