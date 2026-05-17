from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from src.models.product import ProductStatus

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
    active_quantity: int

class ProductCreateRequest(BaseModel):
    category_id: Optional[str] = None
    title: Optional[str] = None
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
    status: ProductStatus
    images: List[ProductImageResponse]
    characteristics: List[ProductCharacteristicResponse]
    skus: List[SKUShortResponse]
    created_at: datetime
    updated_at: datetime

class ProductImageUpdateRequest(BaseModel):
    url: Optional[str] = None
    ordering: Optional[int] = Field(None, ge=0)

class ProductImageCreateRequest(BaseModel):
    url: str
    ordering: int = 0

class ProductShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    status: ProductStatus
    category_id: UUID
    deleted: bool
    created_at: datetime
    min_price: int | None = None
    cover_image: str | None = None

class ProductPaginatedResponse(BaseModel):
    total_count: int
    items: list[ProductShortResponse]
    limit: int
    offset: int