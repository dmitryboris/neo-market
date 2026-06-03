from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from src.models.invoice import InvoiceStatus


class InvoiceItemCreate(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., ge=1)


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku_id: UUID
    quantity: int
    accepted_quantity: int


class InvoiceCreate(BaseModel):
    items: list[InvoiceItemCreate] = Field(..., min_length=1)


class InvoiceAcceptItem(BaseModel):
    invoice_item_id: UUID
    accepted_quantity: int = Field(..., ge=0)


class InvoiceAcceptRequest(BaseModel):
    accepted_items: list[InvoiceAcceptItem] | None = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    status: InvoiceStatus
    items: list[InvoiceItemResponse]
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None = None
    accepted_by: UUID | None = None


class InvoicePaginatedResponse(BaseModel):
    items: list[InvoiceResponse]
    total_count: int
    limit: int
    offset: int
