from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ModeratorCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = None
    role: str = "MODERATOR"
    category_specializations: list[UUID] | None = None


class ModeratorUpdateRequest(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    role: str | None = None
    category_specializations: list[UUID] | None = None


class ModeratorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str | None
    role: str
    is_active: bool
    category_specializations: list[UUID] | None = None
    created_at: datetime
    updated_at: datetime | None


class PaginatedModerators(BaseModel):
    items: list[ModeratorResponse]
    total_count: int
    limit: int
    offset: int
