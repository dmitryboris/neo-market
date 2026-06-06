from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from src.models.product import ProductStatus
from src.schemas.sku import SKUResponse, SKUPublicResponse
from src.schemas.characteristic import Characteristic, CharacteristicResponse


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    ordering: int


class ProductImageCreate(BaseModel):
    url: str
    ordering: int = 0


class ProductCreate(BaseModel):
    category_id: str | None = None
    title: str | None = None
    description: str = Field(..., min_length=1, max_length=5000)
    slug: str | None = None
    images: list[ProductImageCreate] = Field(default_factory=list)
    characteristics: list[Characteristic] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    category_id: str | None = None
    characteristics: list[Characteristic] | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    category_id: UUID
    title: str
    slug: str
    description: str
    status: ProductStatus
    deleted: bool
    blocking_reason_id: UUID | None
    moderator_comment: str | None
    images: list[ProductImageResponse]
    characteristics: list[CharacteristicResponse]
    skus: list[SKUResponse]
    created_at: datetime
    updated_at: datetime


class ProductPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    category_id: UUID
    title: str
    slug: str
    description: str
    status: ProductStatus
    images: list[ProductImageResponse]
    characteristics: list[CharacteristicResponse]
    skus: list[SKUPublicResponse]
    created_at: datetime
    updated_at: datetime


class ProductShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    status: ProductStatus
    category_id: UUID
    deleted: bool
    created_at: datetime
    min_price: int | None = None
    cover_image: str | None = None


class ProductPublicShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    status: ProductStatus
    category_id: UUID
    min_price: int
    cover_image: str | None = None
    created_at: datetime


class ProductPaginatedResponse(BaseModel):
    total_count: int
    items: list[ProductShortResponse]
    limit: int
    offset: int


class ProductPublicPaginatedResponse(BaseModel):
    items: list[ProductPublicShortResponse]
    total_count: int
    limit: int
    offset: int


class BatchProductRequest(BaseModel):
    product_ids: list[UUID] = Field(..., max_length=100)