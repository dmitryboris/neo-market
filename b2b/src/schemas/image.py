from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    url: str
    ordering: int
    
class ProductImageCreateRequest(BaseModel):
    url: str
    ordering: int = 0


class ProductImageUpdateRequest(BaseModel):
    url: str | None = None
    ordering: int | None = None


class SKUImageResponse(BaseModel):
    id: UUID
    url: str
    ordering: int

class SKUImageCreateRequest(BaseModel):
    url: str
    ordering: int = 0

class SKUImageUpdateRequest(BaseModel):
    url: str | None = None
    ordering: int | None = None