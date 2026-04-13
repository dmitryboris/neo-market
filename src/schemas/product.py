from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from src.models.product import ProductStatus
 
class CategoryResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
 
class ProductImageResponse(BaseModel):
    url: str
    ordering: int
    model_config = ConfigDict(from_attributes=True)
 
class CharacteristicResponse(BaseModel):
    name: str
    value: str
    model_config = ConfigDict(from_attributes=True)
 
class SKUResponse(BaseModel):
    id: int
    name: str
    price: int
    active_quantity: int
    characteristics: List[CharacteristicResponse]
    model_config = ConfigDict(from_attributes=True)
 
class ProductResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: ProductStatus
    category: CategoryResponse
    images: List[ProductImageResponse]
    characteristics: List[CharacteristicResponse]
    skus: List[SKUResponse]
    model_config = ConfigDict(from_attributes=True)
 
class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: int
    characteristics: List[CharacteristicResponse] = []
    images: List[str] = []  # список URL
 
class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[ProductStatus] = None