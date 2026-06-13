import uuid
from datetime import datetime
from typing import Any
from enum import StrEnum
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base, UUIDMixin, TimestampMixin


class TicketStatus(StrEnum):
    PENDING = 'PENDING'
    IN_REVIEW = 'IN_REVIEW'
    APPROVED = 'APPROVED'
    BLOCKED = 'BLOCKED'
    HARD_BLOCKED = 'HARD_BLOCKED'
    ARCHIVED = 'ARCHIVED'


class FieldReportName(StrEnum):
    TITLE = 'title'
    DESCRIPTION = 'description'
    PRODUCT_IMAGES = 'product_images'
    CATEGORY = 'category'
    SKU_NAME = 'sku_name'
    SKU_IMAGE = 'sku_image'
    SKU_PRICE = 'sku_price'


class TicketKind(StrEnum):
    CREATE = 'CREATE'
    EDIT = 'EDIT'


class Ticket(UUIDMixin, TimestampMixin, Base):
    """Тикет модерации — карточка товара, ждущая решения модератора."""

    __tablename__ = 'tickets'
    __table_args__ = (CheckConstraint('queue_priority BETWEEN 1 AND 4', name='ck_tickets_queue_priority_range'),)

    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    kind: Mapped[TicketKind] = mapped_column(
        String(8),
        nullable=False,
        default=TicketKind.CREATE,
        server_default=TicketKind.CREATE,
    )
    status: Mapped[TicketStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TicketStatus.PENDING,
        server_default=TicketStatus.PENDING,
        index=True,
    )
    queue_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default='3')
    claimed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('moderators.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocking_reason_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('blocking_reasons.id', ondelete='RESTRICT'),
        nullable=True,
    )
    moderator_comment: Mapped[str | None] = mapped_column(Text(), nullable=True)
    field_reports: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default='[]')
    json_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    json_after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default='{}')
