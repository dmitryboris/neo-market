import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, Uuid, Enum
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class OrderStatus(StrEnum):
    """Статусы заказа покупателя"""

    CREATED = 'CREATED'
    PAID = 'PAID'
    ASSEMBLING = 'ASSEMBLING'
    DELIVERING = 'DELIVERING'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'
    CANCEL_PENDING = 'CANCEL_PENDING'


class Order(UUIDMixin, TimestampMixin, Base):
    """Заказ покупателя.

    Идемпотентность checkout: UNIQUE-индекс на `idempotency_key` — повторный POST
    с тем же ключом возвращает существующий заказ (см. ADR в этом PR).
    """

    __tablename__ = 'orders'

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey('buyers.id'), index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED, index=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    delivery_address: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    address_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
