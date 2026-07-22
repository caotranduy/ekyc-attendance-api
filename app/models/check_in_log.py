import uuid
import datetime
import uuid6
from sqlalchemy import ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class CheckInLog(Base):
    """Represents a daily attendance check-in log entry for a user."""
    __tablename__ = "check_in_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid6.uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    check_in_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False
    )
    check_in_date: Mapped[datetime.date] = mapped_column(
        Date,
        default=lambda: datetime.datetime.utcnow().date(),
        nullable=False,
        index=True
    )

    # Relationship back to User model
    user: Mapped["User"] = relationship("User", back_populates="check_in_logs")
