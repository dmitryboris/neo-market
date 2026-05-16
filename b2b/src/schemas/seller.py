from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime

class SellerCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    company_name: str
    inn: str
    phone: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_name_parts(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("First and last name cannot be empty")
        return normalized

    @field_validator("middle_name")
    @classmethod
    def validate_middle_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("inn")
    @classmethod
    def validate_inn(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit() or len(normalized) not in (10, 12):
            raise ValueError("INN must contain 10 or 12 digits")
        return normalized

class SellerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    company_name: str | None = None
    phone: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_optional_required_name_parts(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("First and last name cannot be empty")
        return normalized

    @field_validator("middle_name")
    @classmethod
    def validate_optional_middle_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

class SellerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    company_name: str
    inn: str
    phone: str | None
    created_at: datetime
    updated_at: datetime