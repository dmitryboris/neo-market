from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from src.schemas.image import SKUImageCreateRequest

class SKUCharacteristicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)

class SKUCharacteristicResponse(BaseModel):
    id: UUID
    name: str
    value: str

class SKUImageResponse(BaseModel):
    id: UUID
    url: str
    ordering: int

class SKUCreateRequest(BaseModel):
    product_id: UUID
    name: str | None = None
    price: int | None = None
    cost_price: int | None = None
    discount: int = 0
    article: str | None = Field(None, max_length=100)
    images: list[SKUImageCreateRequest] = Field(default_factory=list)
    characteristics: Optional[List[SKUCharacteristicCreate]] = Field(default_factory=list)

class SKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    name: str
    price: int
    cost_price: int
    discount: int
    stock_quantity: int
    active_quantity: int
    reserved_quantity: int
    article: str | None = None
    characteristics: List[SKUCharacteristicResponse] = []
    images: List[SKUImageResponse] = []
    created_at: datetime
    updated_at: datetime

class SKUUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[int] = Field(None, gt=0)
    discount: Optional[int] = Field(None, ge=0)
