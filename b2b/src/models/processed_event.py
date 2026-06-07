import uuid
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base
from datetime import datetime

class ProcessedModerationEvent(Base):
    __tablename__ = "processed_moderation_events"

    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sender_service: Mapped[str] = mapped_column(String(50), primary_key=True)