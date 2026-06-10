from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from src.database import get_session
from src.schemas.auth import (
    BuyerRegisterRequest, LoginRequest, RefreshRequest, TokenResponse, LogoutRequest
)
from src.services.auth_service import (
    register_buyer, login_buyer, refresh_token_pair, logout_buyer
)
from src.dependencies import get_current_user, get_token_payload
from src.models.buyer import Buyer

from shared.exceptions import DomainException

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
        request: BuyerRegisterRequest,
        session: AsyncSession = Depends(get_session),
):
    return await register_buyer(request=request, session=session)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
        request: LoginRequest,
        session: AsyncSession = Depends(get_session),
        x_session_id: str | None = Header(None, alias="X-Session-Id"),
):
    return await login_buyer(request=request, session=session, x_session_id=x_session_id)


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
        request: RefreshRequest,
        session: AsyncSession = Depends(get_session),
):
    return await refresh_token_pair(refresh_token_str=request.refresh_token, session=session)


@auth_router.post("/logout", status_code=204)
async def logout(
        request: LogoutRequest,
        access_payload: dict = Depends(get_token_payload),
        session: AsyncSession = Depends(get_session),
):
    await logout_buyer(access_payload=access_payload, refresh_token_str=request.refresh_token, session=session)
    return None


@auth_router.post("/token", response_model=TokenResponse)
async def token_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_session),
):
    request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login_buyer(request=request, session=session)
