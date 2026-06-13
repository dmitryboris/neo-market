from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class ApproveRequest(BaseModel):
    comment: str | None = Field(None, max_length=2000)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    seller_id: UUID
    category_id: UUID | None
    kind: str
    status: str
    queue_priority: int
    claimed_by: UUID | None
    claimed_at: datetime | None
    claim_expires_at: datetime | None
    decision_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
