from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.models import Seller
from src.dependencies import get_current_user, get_token_payload
from src.services.auth_service import register_seller, login_seller, logout_seller, get_token, refresh_token, get_seller
from src.schemas.auth import RegisterResponse, RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, \
    LogoutRequest

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Seller's register"
)
async def register(
        request: RegisterRequest,
        session: AsyncSession = Depends(get_session)
):
    return await register_seller(request, session)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
        request: LoginRequest,
        session: AsyncSession = Depends(get_session)
):
    return await login_seller(request, session)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh tokens"
)
async def refresh(
        request: RefreshRequest,
        session: AsyncSession = Depends(get_session)
):
    return await refresh_token(request.refresh_token, session)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
        request: LogoutRequest,
        access_payload: dict = Depends(get_token_payload),
        session: AsyncSession = Depends(get_session)
):
    await logout_seller(access_payload, request.refresh_token, session)
    return None


@auth_router.post(
    "/token",
    response_model=TokenResponse
)
async def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_session)
):
    request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login_seller(request, session)
