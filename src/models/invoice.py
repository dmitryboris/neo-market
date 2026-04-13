import enum
from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class InvoiceStatus(str, enum.Enum): # точно такие??
    CREATED = "CREATED"
    ON_MODERATION = "ON_MODERATION"
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"))
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    seller: Mapped["Seller"] = relationship(lazy="joined")
    items: Mapped[List["InvoiceItem"]] = relationship(cascade="all, delete-orphan")
