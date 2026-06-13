from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Moderator, RefreshToken, RefreshBlacklist
from src.config import settings
from src.schemas.auth import (
    ModeratorRegisterRequest, LoginRequest, TokenResponse
)
from shared.security import TokenService, hash_password, verify_password
from shared.enums import UserRole
from shared.exceptions import (
    InvalidCredentials, UserBlocked, EmailAlreadyExists,
    TokenInvalid, TokenExpired, TokenRevoked
)

from uuid import UUID

token_service = TokenService(
    secret=settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
    access_ttl_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_ttl_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


async def get_moderator(email: str, session: AsyncSession) -> Moderator | None:
    stmt = select(Moderator).where(Moderator.email == email)
    result = await session.execute(stmt)
    return result.scalars().first()


async def register_moderator(request: ModeratorRegisterRequest, session: AsyncSession) -> TokenResponse:
    existing = await get_moderator(request.email, session)
    if existing:
        raise EmailAlreadyExists()

    moderator = Moderator(
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole.MODERATOR.value,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        is_active=True,
    )
    session.add(moderator)
    await session.flush()

    access_token = token_service.create_access_token(str(moderator.id), moderator.role)
    refresh_token = token_service.create_refresh_token(str(moderator.id), moderator.role)

    refresh_payload = token_service.decode_token(refresh_token)
    rt = RefreshToken(
        jti=refresh_payload["jti"],
        moderator_id=moderator.id,
        issued_at=datetime.fromtimestamp(refresh_payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    )
    session.add(rt)
    await session.commit()

    return TokenResponse(
        user_id=str(moderator.id),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_type="Bearer",
    )


async def login_moderator(request: LoginRequest, session: AsyncSession) -> TokenResponse:
    moderator = await get_moderator(request.email, session)
    if not moderator or not verify_password(request.password, moderator.password_hash):
        raise InvalidCredentials()
    if not moderator.is_active:
        raise UserBlocked()

    access_token = token_service.create_access_token(str(moderator.id), moderator.role)
    refresh_token = token_service.create_refresh_token(str(moderator.id), moderator.role)

    refresh_payload = token_service.decode_token(refresh_token)
    rt = RefreshToken(
        jti=refresh_payload["jti"],
        moderator_id=moderator.id,
        issued_at=datetime.fromtimestamp(refresh_payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    )
    session.add(rt)
    await session.flush()

    await session.commit()

    return TokenResponse(
        user_id=str(moderator.id),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_token_pair(refresh_token_str: str, session: AsyncSession) -> TokenResponse:
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

    user_id = str(rt.moderator_id)
    role = payload.get("role")
    new_access = token_service.create_access_token(user_id, role)
    new_refresh = token_service.create_refresh_token(user_id, role)

    blacklist_entry = RefreshBlacklist(jti=jti, expires_at=rt.expires_at)
    session.add(blacklist_entry)
    await session.delete(rt)

    new_payload = token_service.decode_token(new_refresh)
    new_rt = RefreshToken(
        jti=new_payload["jti"],
        moderator_id=rt.moderator_id,
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


async def logout_moderator(access_payload: dict, refresh_token_str: str, session: AsyncSession) -> None:
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
        blacklist_entry = RefreshBlacklist(jti=jti, expires_at=rt.expires_at)
        session.add(blacklist_entry)
        await session.delete(rt)
    else:
        blacklist_entry = RefreshBlacklist(
            jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        session.add(blacklist_entry)
    await session.commit()


async def get_moderator_by_id(session: AsyncSession, moderator_id: UUID) -> Moderator | None:
    stmt = select(Moderator).where(Moderator.id == moderator_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()