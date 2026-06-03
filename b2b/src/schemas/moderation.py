from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from src.models.product import ProductStatus
from src.schemas.characteristic import CharacteristicResponse
from src.schemas.sku import SKUResponse
from src.schemas.produce import ProductImageResponse


class ModerationEventType(str, Enum):
    MODERATED = "MODERATED"
    BLOCKED = "BLOCKED"


class ModerationEventRequest(BaseModel):
    idempotency_key: UUID
    product_id: UUID
    event_type: ModerationEventType
    occurred_at: datetime
    moderator_id: UUID | None = None
    moderator_comment: str | None = None
    blocking_reason_id: UUID | None = None
    hard_block: bool = False
    field_reports: list["FieldReport"] | None = None


class FieldReport(BaseModel):
    field_name: str
    comment: str
    sku_id: UUID | None = None


class BlockingReason(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    comment: str


class ProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    category_id: UUID
    title: str
    slug: str
    description: str
    status: ProductStatus
    deleted: bool
    images: list[ProductImageResponse]
    characteristics: list[CharacteristicResponse]
    skus: list[SKUResponse]
    created_at: datetime
    updated_at: datetime

    blocked: bool
    blocking_reason: BlockingReason | None
    field_reports: list[FieldReport]
