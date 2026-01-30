"""SymptomLog model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class SymptomLog(Base):
    """Symptom tracking log."""

    __tablename__ = "symptom_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    symptom: Mapped[str] = mapped_column(String, nullable=False, comment="e.g., 'Зуд', 'Сыпь'")
    severity: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5 scale")

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="symptom_logs")
