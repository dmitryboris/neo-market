from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.database import get_session
from src.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, LogoutRequest, TokenResponse
from src.models import Seller, RefreshToken
from src.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.dependencies import get_current_user
from src.config import settings
from sqlalchemy import select

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session)):
    stmt = select(Seller).where((Seller.email == req.email) | (Seller.inn == req.inn))
    result = await session.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_OR_INN_EXISTS", "message": "Email или ИНН уже зарегистрированы"},
        )

    seller = Seller(
        email=req.email,
        password_hash=hash_password(req.password),
        role="seller",
        company_name=req.company_name,
        inn=req.inn,
        first_name=req.first_name,
        last_name=req.last_name,
        phone=req.phone,
    )
    session.add(seller)
    await session.flush()

    access_token = create_access_token(str(seller.id), seller.role)
    refresh_token = create_refresh_token(str(seller.id), seller.role)

    decoded_refresh = decode_token(refresh_token)
    rt = RefreshToken(
        jti=decoded_refresh["jti"],
        user_id=seller.id,
        issued_at=datetime.fromtimestamp(decoded_refresh["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(decoded_refresh["exp"], tz=timezone.utc),
    )
    session.add(rt)
    await session.commit()

    return TokenResponse(
        user_id=str(seller.id),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    stmt = select(Seller).where(Seller.email == req.email)
    result = await session.execute(stmt)
    seller = result.scalars().first()

    if not seller or not verify_password(req.password, seller.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Неверные учётные данные"},
        )
    if not seller.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_BLOCKED", "message": "Пользователь заблокирован"},
        )

    access_token = create_access_token(str(seller.id), seller.role)
    refresh_token = create_refresh_token(str(seller.id), seller.role)

    decoded_refresh = decode_token(refresh_token)
    rt = RefreshToken(
        jti=decoded_refresh["jti"],
        user_id=seller.id,
        issued_at=datetime.fromtimestamp(decoded_refresh["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(decoded_refresh["exp"], tz=timezone.utc),
    )
    session.add(rt)
    await session.commit()

    return TokenResponse(
        user_id=str(seller.id),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, session: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(req.refresh_token)
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

    from sqlalchemy import select
    stmt = select(RefreshToken).where(RefreshToken.jti == jti)
    result = await session.execute(stmt)
    rt = result.scalars().first()

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

    # Revoke old token
    rt.revoked = True
    session.add(rt)

    user_id = str(rt.user_id)
    role = payload.get("role", "seller")
    new_access = create_access_token(user_id, role)
    new_refresh = create_refresh_token(user_id, role)

    decoded_new = decode_token(new_refresh)
    new_rt = RefreshToken(
        jti=decoded_new["jti"],
        user_id=rt.user_id,
        issued_at=datetime.fromtimestamp(decoded_new["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(decoded_new["exp"], tz=timezone.utc),
    )
    session.add(new_rt)
    await session.commit()

    return TokenResponse(
        user_id=user_id,
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: LogoutRequest, current_user: Seller = Depends(get_current_user),
                 session: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(req.refresh_token)
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

    jti = payload.get("jti")
    if jti:
        from sqlalchemy import select
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await session.execute(stmt)
        rt = result.scalars().first()
        if rt:
            rt.revoked = True
            session.add(rt)
            await session.commit()
    return
