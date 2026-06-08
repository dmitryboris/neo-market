from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from enum import StrEnum, auto
from src.database import Base, UUIDMixin, TimestampMixin


class UserRole(StrEnum):
    """Роли пользователей NeoMarket. В каждом сервисе используется подмножество.

    - SELLER — продавец в B2B
    - BUYER — покупатель в B2C
    - MODERATOR — модератор в Moderation
    - ADMIN — суперпользователь, общий для всех сервисов
    """

    SELLER = auto()
    BUYER = auto()
    MODERATOR = auto()
    ADMIN = auto()


class Buyer(UUIDMixin, TimestampMixin, Base):
    """Buyer (покупатель) — единая таблица users в b2c."""

    __tablename__ = 'buyers'

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
