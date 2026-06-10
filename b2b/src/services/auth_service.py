from datetime import datetime, timezone, timedelta
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import RefreshToken, Seller, RefreshBlacklist
from src.config import settings
from src.database import get_session
from src.schemas.auth import RegisterResponse, RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, \
    LogoutRequest

from shared.security import hash_password, verify_password, TokenService
from shared.exceptions import (
    InvalidCredentials, UserBlocked, EmailAlreadyExists,
    TokenInvalid, TokenExpired, TokenRevoked
)

token_service = TokenService(
    secret=settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
    access_ttl_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_ttl_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


async def get_seller(
        request: RegisterRequest,
        session: AsyncSession = Depends(get_session)
) -> Seller | None:
    stmt = select(Seller).where((Seller.email == request.email) | (Seller.inn == request.inn))
    result = await session.execute(stmt)
    return result.scalars().first()


async def register_seller(
        request: RegisterRequest,
        session: AsyncSession = Depends(get_session)
) -> RegisterResponse:
    existing = await get_seller(request, session)
    if existing:
        raise EmailAlreadyExists(code="EMAIL_OR_INN_EXISTS", message="Email or INN already exists")

    seller = Seller(
        email=request.email,
        password_hash=hash_password(request.password),
        role="SELLER",
        company_name=request.company_name,
        inn=request.inn,
        first_name=request.first_name,
        middle_name=request.middle_name,
        last_name=request.last_name,
        phone=request.phone,
        is_active=True
    )
    session.add(seller)
    await session.flush()

    access_token = token_service.create_access_token(str(seller.id), seller.role)
    refresh_token = token_service.create_refresh_token(str(seller.id), seller.role)

    decoded_refresh = token_service.decode_token(refresh_token)
    rt = RefreshToken(
        jti=decoded_refresh["jti"],
        seller_id=seller.id,
        issued_at=datetime.fromtimestamp(decoded_refresh["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(decoded_refresh["exp"], tz=timezone.utc),
    )
    session.add(rt)
    await session.commit()

    return RegisterResponse(
        id=seller.id,
        email=seller.email,
        first_name=seller.first_name,
        last_name=seller.last_name,
        middle_name=seller.middle_name,
        company_name=seller.company_name,
        inn=seller.inn,
        phone=seller.phone,
        created_at=seller.created_at,
        updated_at=seller.updated_at,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def login_seller(
        request: LoginRequest,
        session: AsyncSession
) -> TokenResponse:
    stmt = select(Seller).where(Seller.email == request.email)
    result = await session.execute(stmt)
    seller = result.scalars().first()

    if not seller or not verify_password(request.password, seller.password_hash):
        raise InvalidCredentials()
    if not seller.is_active:
        raise UserBlocked()

    access_token = token_service.create_access_token(str(seller.id), seller.role)
    refresh_token = token_service.create_refresh_token(str(seller.id), seller.role)

    decoded_refresh = token_service.decode_token(refresh_token)
    rt = RefreshToken(
        jti=decoded_refresh["jti"],
        seller_id=seller.id,
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


async def get_token(payload: dict, session: AsyncSession):
    jti = payload.get("jti")
    stmt = select(RefreshToken).where(RefreshToken.jti == jti)
    result = await session.execute(stmt)
    return result.scalars().first()


async def refresh_token(
        refresh_token_str: str,
        session: AsyncSession
) -> TokenResponse:
    payload = token_service.decode_token(refresh_token_str)
    jti = payload.get("jti")
    if not jti:
        raise TokenInvalid(message="Refresh token missing jti")

    blacklist_stmt = select(RefreshBlacklist).where(RefreshBlacklist.jti == jti)
    blacklist_result = await session.execute(blacklist_stmt)
    if blacklist_result.scalar_one_or_none():
        raise TokenRevoked()

    rt_stmt = select(RefreshToken).where(RefreshToken.jti == jti)
    rt_result = await session.execute(rt_stmt)
    rt = rt_result.scalar_one_or_none()
    if not rt:
        raise TokenRevoked()

    if rt.expires_at < datetime.now(timezone.utc):
        raise TokenExpired()

    user_id = str(rt.seller_id)
    role = payload.get("role")
    new_access = token_service.create_access_token(user_id, role)
    new_refresh = token_service.create_refresh_token(user_id, role)

    blacklist_entry = RefreshBlacklist(
        jti=jti,
        expires_at=rt.expires_at,
    )
    session.add(blacklist_entry)

    await session.delete(rt)

    new_payload = token_service.decode_token(new_refresh)
    new_rt = RefreshToken(
        jti=new_payload["jti"],
        seller_id=rt.seller_id,
        issued_at=datetime.fromtimestamp(new_payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc),
    )
    session.add(new_rt)
    await session.commit()

    return TokenResponse(
        user_id=user_id,
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def logout_seller(
        access_payload: dict,
        refresh_token_str: str,
        session: AsyncSession
) -> None:
    refresh_payload = token_service.decode_token(refresh_token_str)

    if refresh_payload.get("sub") != access_payload.get("sub"):
        raise TokenInvalid(message="Refresh token does not match current user")

    jti = refresh_payload.get("jti")
    if not jti:
        raise TokenInvalid(message="Refresh token missing jti")

    rt_stmt = select(RefreshToken).where(RefreshToken.jti == jti)
    rt_result = await session.execute(rt_stmt)
    rt = rt_result.scalar_one_or_none()
    if rt:
        blacklist_entry = RefreshBlacklist(
            jti=jti,
            expires_at=rt.expires_at,
        )
        session.add(blacklist_entry)
        await session.delete(rt)
    else:
        blacklist_entry = RefreshBlacklist(
            jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        session.add(blacklist_entry)

    await session.commit()
