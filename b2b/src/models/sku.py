from typing import TYPE_CHECKING, List

import uuid
from sqlalchemy import ForeignKey, BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from .product import Product
    from .sku_image import SKUImage
    from .sku_characteristic import SKUCharacteristic
    from .invoice import InvoiceItem


class SKU(Base, TimestampMixin):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped["Product"] = relationship(back_populates="skus")
    images: Mapped[list["SKUImage"]] = relationship(
        back_populates="sku", cascade="all, delete-orphan"
    )
    characteristics: Mapped[list["SKUCharacteristic"]] = relationship(
        back_populates="sku", cascade="all, delete-orphan"
    )
    invoice_items: Mapped[list["InvoiceItem"]] = relationship(back_populates="sku")
