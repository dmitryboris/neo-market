from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Literal, Optional

class InventoryItem(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., gt=0)

class ReserveRequest(BaseModel):
    idempotency_key: UUID
    order_id: UUID
    items: list[InventoryItem] = Field(..., min_length=1)

class ReserveResponse(BaseModel):
    order_id: UUID
    status: Literal["RESERVED"]
    reserved_at: datetime

class InventoryOrderRequest(BaseModel):
    order_id: UUID
    items: list[InventoryItem] = Field(..., min_length=1)

class InventoryOrderResponse(BaseModel):
    order_id: UUID
    status: Literal["UNRESERVED", "FULFILLED"]
    processed_at: datetime