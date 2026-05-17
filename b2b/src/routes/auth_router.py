from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.models import Seller, RefreshToken
from src.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.dependencies import get_current_user
from src.config import settings
from src.services.auth_service import register, login, logout, get_token, refresh_token, get_seller
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
    seller = await get_seller(request, session)
    if seller:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_OR_INN_EXISTS", "message": "Email или ИНН уже зарегистрированы"},
        )
    return await register(request, session)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
        request: LoginRequest,
        session: AsyncSession = Depends(get_session)
):
    return await login(request, session)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh tokens"
)
async def refresh(
        request: RefreshRequest,
        session: AsyncSession = Depends(get_session)
):
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Невалидный refresh токен"},
        )
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Нет jti в refresh токене"},
        )

    rt = await get_token(payload, session)

    if not rt or rt.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "Refresh токен уже использован или отозван"},
        )
    if rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Рефреш токен истёк"},
        )

    return await refresh_token(rt, payload, session)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
        request: LogoutRequest,
        current_user: Seller = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Невалидный refresh токен"},
        )
    if payload.get("sub") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Refresh токен не принадлежит текущему пользователю"},
        )

    return await logout(payload, session)


@auth_router.post(
    "/token",
    response_model=TokenResponse
)
async def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_session)
):
    request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login(request, session)
