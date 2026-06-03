from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from src.schemas.characteristic import Characteristic, CharacteristicResponse


class SKUImageCreate(BaseModel):
    url: str
    ordering: int = 0


class SKUImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    ordering: int


class SKUCreate(BaseModel):
    product_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=0)
    cost_price: int | None = None
    discount: int = Field(default=0, ge=0)
    article: str | None = None
    images: list[SKUImageCreate] = Field(default_factory=list)
    characteristics: list[Characteristic] = Field(default_factory=list)


class SKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    name: str
    price: int
    discount: int
    cost_price: int | None
    stock_quantity: int
    active_quantity: int
    reserved_quantity: int
    article: str | None
    images: list[SKUImageResponse]
    characteristics: list[CharacteristicResponse]
    created_at: datetime
    updated_at: datetime


class SKUPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    name: str
    price: int
    discount: int
    stock_quantity: int
    active_quantity: int
    article: str | None
    images: list[SKUImageResponse]
    characteristics: list[CharacteristicResponse]


class SKUUpdate(BaseModel):
    name: str | None = None
    price: int | None = Field(default=None, ge=0)
    discount: int | None = Field(default=None, ge=0)
    cost_price: int | None = None
    article: str | None = None
    characteristics: list[Characteristic] | None = None
