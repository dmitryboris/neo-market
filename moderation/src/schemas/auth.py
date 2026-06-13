from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: UUID


class LogoutRequest(BaseModel):
    refresh_token: str
