from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import StrEnum
from typing import Union


class B2BEventType(StrEnum):
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_EDITED = "PRODUCT_EDITED"
    PRODUCT_DELETED = "PRODUCT_DELETED"


class EventProductCreated(BaseModel):
    product_id: UUID
    seller_id: UUID
    category_id: UUID | None = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_after: dict = Field(default_factory=dict)


class EventProductEdited(BaseModel):
    product_id: UUID
    seller_id: UUID
    category_id: UUID | None = None
    queue_priority: int = Field(default=3, ge=1, le=4)
    json_before: dict
    json_after: dict


class EventProductDeleted(BaseModel):
    product_id: UUID


class IncomingB2BEvent(BaseModel):
    event_type: B2BEventType
    idempotency_key: UUID
    occurred_at: datetime
    payload: Union[EventProductCreated, EventProductEdited, EventProductDeleted]
