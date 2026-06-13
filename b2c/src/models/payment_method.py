import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class PaymentMethod(UUIDMixin, TimestampMixin, Base):
    """Платёжный метод покупателя — ТОЛЬКО МЕТАДАННЫЕ"""

    __tablename__ = 'payment_methods'

    buyer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey('buyers.id'), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(32), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    exp_year: Mapped[int] = mapped_column(Integer, nullable=False)
    exp_month: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    type: Mapped[str] = mapped_column(String(32), nullable=False)
