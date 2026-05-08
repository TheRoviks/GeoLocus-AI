from datetime import time

from sqlalchemy import BigInteger, Boolean, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    quiet_hours_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(23, 0))
    quiet_hours_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(8, 0))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    reminders: Mapped[list["Reminder"]] = relationship(  # type: ignore[name-defined] # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
