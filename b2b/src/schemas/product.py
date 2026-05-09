from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    url: str
    ordering: int

class ProductImageCreate(BaseModel):
    url: str = Field(..., description="Ссылка на изображение")
    ordering: int = Field(..., ge=0, description="Порядок отображения")

class ProductCharacteristicResponse(BaseModel):
    id: UUID
    name: str
    value: str

class ProductCharacteristicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)

class SKUShortResponse(BaseModel):
    id: UUID
    name: str | None = None
    price: int
    stock_quantity: int
    article: str | None = None

class ProductCreateRequest(BaseModel):
    category_id: Optional[str] = None
    title: str
    description: str = Field(..., min_length=1, max_length=5000)
    images: List[ProductImageCreate] | None = None
    characteristics: Optional[List[ProductCharacteristicCreate]] = Field(default_factory=list)

class ProductUpdateRequest(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[str] = None

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    seller_id: UUID
    category_id: UUID
    title: str
    description: str | None = None
    status: str
    images: List[ProductImageResponse]
    characteristics: List[ProductCharacteristicResponse]
    skus: List[SKUShortResponse]
    created_at: datetime
    updated_at: datetime

class ProductMyItemResponse(BaseModel):
    id: UUID
    title: str
    status: str
    category_id: UUID
    created_at: datetime

class ProductMyListResponse(BaseModel):
    total: int
    items: List[ProductMyItemResponse]

class ProductImageUpdateRequest(BaseModel):
    url: Optional[str] = None
    ordering: Optional[int] = Field(None, ge=0)

class ProductImageCreateRequest(BaseModel):
    url: str
    ordering: int = 0