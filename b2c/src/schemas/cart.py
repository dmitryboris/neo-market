from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal

class ImageRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    url: str
    alt: Optional[str] = None
    ordering: int
    is_main: bool

class CartItemAddRequest(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., ge=1)

class CartItemUpdateRequest(BaseModel):
    quantity: int

class CartItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sku_id: UUID
    product_id: UUID
    name: str
    sku_code: Optional[str] = None
    quantity: int
    unit_price: int  
    unit_price_at_add: Optional[int] = None
    line_total: int
    available_quantity: int
    is_available: bool
    image: Optional[ImageRef] = None

class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    items: list[CartItem]
    items_count: int
    subtotal: int
    is_valid: bool
    updated_at: datetime

class CartValidationIssue(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sku_id: UUID
    type: Literal["PRICE_CHANGED", "OUT_OF_STOCK", "QUANTITY_REDUCED", "PRODUCT_BLOCKED", "PRODUCT_DELETED"]
    message: str
    old_value: Optional[int | str] = None
    new_value: Optional[int | str] = None

class CartValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    is_valid: bool
    cart: CartResponse
    issues: list[CartValidationIssue]