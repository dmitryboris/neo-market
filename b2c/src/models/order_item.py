import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class OrderItem(UUIDMixin, TimestampMixin, Base):
    """Позиция заказа.

    `unit_price`, `product_title`, `sku_name`, `product_id` — на момент
    покупки (канон: покупатель видит то, что покупал, даже если продавец
    позже изменил цену или название).
    """

    __tablename__ = 'order_items'

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('orders.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False)
