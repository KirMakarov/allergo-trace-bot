"""SymptomLog model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class SymptomLog(Base):
    """Symptom tracking log."""

    __tablename__ = "symptom_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        nullable=False,
        comment="Stored in UTC",
    )
    symptom: Mapped[str] = mapped_column(String, nullable=False, comment="e.g., 'Itch', 'Rash'")
    severity: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5 scale")

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="symptom_logs")
