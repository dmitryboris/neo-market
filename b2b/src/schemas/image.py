from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ImageEntityType(str, Enum):
    PRODUCT = "PRODUCT"
    SKU = "SKU"


class ImageUploadRequest(BaseModel):
    entity_type: ImageEntityType
    entity_id: UUID | None = None
    ordering: int = 0


class ImageAttachRequest(BaseModel):
    image_id: UUID | None =None
    ordering: int = 0


class ImageUpdateRequest(BaseModel):
    url: str | None = None
    ordering: int | None = None


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    ordering: int
    entity_type: ImageEntityType
    entity_id: UUID | None = None