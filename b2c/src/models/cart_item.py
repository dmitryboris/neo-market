import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class CartItem(UUIDMixin, TimestampMixin, Base):
    """Пункт корзины — ссылка на SKU из B2B + quantity.
    B2C не хранит ни цену, ни название — всё это динамически тащим из B2B
    UNIQUE(cart_id, sku_id) — один SKU не может быть в корзине дважды;
    """

    __tablename__ = 'cart_items'
    __table_args__ = (
        CheckConstraint('quantity >= 1', name='cart_item_quantity_positive'),
        UniqueConstraint('cart_id', 'sku_id', name='uq_cart_items_cart_sku'),
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('carts.id', ondelete='CASCADE'),
        index=True,
        nullable=False,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

