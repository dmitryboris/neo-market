from typing import TYPE_CHECKING

import enum
import uuid
from sqlalchemy import ForeignKey, Enum, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from .seller import Seller
    from .category import Category
    from .sku import SKU
    from .product_characteristic import ProductCharacteristic
    from .product_image import ProductImage
    from .blocking_reason import BlockingReason
    from .field_report import FieldReport


class ProductStatus(str, enum.Enum):
    CREATED = "CREATED"
    ON_MODERATION = "ON_MODERATION"
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    blocking_reason_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blocking_reasons.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), nullable=False, default=ProductStatus.CREATED, index=True
    )
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moderator_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    seller: Mapped["Seller"] = relationship(back_populates="products")
    category: Mapped["Category"] = relationship(back_populates="products")
    blocking_reason: Mapped["BlockingReason | None"] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    characteristics: Mapped[list["ProductCharacteristic"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    skus: Mapped[list["SKU"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    field_reports: Mapped[list["FieldReport"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
