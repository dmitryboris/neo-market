from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.auth import (
    BuyerRegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from src.services import auth_service
from src.dependencies import get_current_buyer
from src.models.buyer import Buyer

from shared.exceptions import DomainException

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    request: BuyerRegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.register_buyer(session, request)



@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
):
    return await auth_service.login_buyer(session, request)



@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.refresh_access_token(session, request.refresh_token)


@auth_router.post("/logout", status_code=204)
async def logout(
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Header(None, alias="Refresh-Token"),
    current_buyer: Buyer = Depends(get_current_buyer),
):
    await auth_service.logout_buyer(session, refresh_token)
    return None