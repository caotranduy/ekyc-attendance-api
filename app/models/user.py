import uuid
import uuid6
import datetime
from sqlalchemy import String, Uuid, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class User(Base):
    """SQLAlchemy model mapping user account details, credentials, and their registered face ID.
    
    Attributes:
        id (uuid.UUID): Primary key, unique identifier of the user (UUIDv7).
        name (str): The display/full name of the user.
        username (str, optional): The unique login username.
        email (str, optional): The unique email address.
        hashed_password (str, optional): The bcrypt hashed password for credentials login.
        is_active (bool): Flag indicating if the account is active.
        is_admin (bool): Flag indicating if the user has administrative privileges.
        created_at (datetime.datetime): Timestamp when the user account was created.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid6.uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Login & Auth fields (optional/nullable for flexible flow support)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Status & Authorization flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Time audit
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    face: Mapped["UserFace"] = relationship("UserFace", back_populates="user", uselist=False, cascade="all, delete-orphan")


