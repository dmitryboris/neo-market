from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal

class CartItemAddRequest(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., ge=1)

class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(..., ge=1)

class CartItemResponse(BaseModel):
    sku_id: UUID
    product_id: UUID
    name: str
    sku_code: Optional[str] = None
    quantity: int
    unit_price: int                    # копейки
    unit_price_at_add: Optional[int] = None
    line_total: int
    available_quantity: int
    is_available: bool
    image: Optional["ImageRef"] = None   # определим ниже

class CartResponse(BaseModel):
    id: UUID
    items: list[CartItemResponse]
    items_count: int                    # сумма quantity
    subtotal: int
    is_valid: bool
    updated_at: datetime

class ImageRef(BaseModel):
    id: UUID
    url: str
    alt: Optional[str] = None
    ordering: int
    is_main: bool

class CartValidationIssue(BaseModel):
    sku_id: UUID
    type: Literal["PRICE_CHANGED", "OUT_OF_STOCK", "QUANTITY_REDUCED", "PRODUCT_BLOCKED", "PRODUCT_DELETED"]
    message: str
    old_value: Optional[int | str] = None
    new_value: Optional[int | str] = None

class CartValidationResponse(BaseModel):
    is_valid: bool
    cart: CartResponse
    issues: list[CartValidationIssue]

CartItemResponse.model_rebuild()
CartResponse.model_rebuild()