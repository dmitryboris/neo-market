import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .product import Product
    from .sku import SKU


class FieldReport(Base):
    __tablename__ = "field_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sku_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skus.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="field_reports")
    sku: Mapped["SKU | None"] = relationship()
