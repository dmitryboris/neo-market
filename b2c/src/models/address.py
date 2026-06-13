import uuid

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class Address(UUIDMixin, TimestampMixin, Base):
    """Адрес доставки покупателя. buyer_id ссылается на buyers.id."""

    __tablename__ = 'addresses'

    buyer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey('buyers.id'), index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str | None] = mapped_column(String(200),nullable=True)
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    street: Mapped[str] = mapped_column(String(200), nullable=False)
    building: Mapped[str] = mapped_column(String(50),nullable=False)
    apartment: Mapped[str | None] = mapped_column(String(50),nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(200),nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
