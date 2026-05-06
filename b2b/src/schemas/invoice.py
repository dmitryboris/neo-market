from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from models.invoice import InvoiceStatus


class InvoiceItemCreate(BaseModel):
    sku_id: UUID
    quantity: int

    @field_validator("quantity")
    @classmethod
    def ensure_quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku_id: UUID
    quantity: int


class InvoiceCreate(BaseModel):
    items: list[InvoiceItemCreate]

    @field_validator("items")
    @classmethod
    def ensure_items_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Invoice must contain at least one item")
        return v
    
    @field_validator("items")
    @classmethod
    def ensure_no_duplicate_skus(cls, v: list) -> list:
        sku_ids = [item.sku_id for item in v]
        if len(sku_ids) != len(set(sku_ids)):
            raise ValueError("Duplicate SKU IDs in invoice items")
        return v


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    status: InvoiceStatus
    items: list[InvoiceItemResponse]
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    total: int
    items: list[InvoiceResponse]
