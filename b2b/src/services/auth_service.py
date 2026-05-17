from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends
from sqlalchemy.engine.row import Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import RefreshToken, Seller
from src.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.config import settings
from src.database import get_session
from src.schemas.auth import RegisterResponse, RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, \
    LogoutRequest


async def get_seller(request: RegisterRequest, session: AsyncSession = Depends(get_session)):
    stmt = select(Seller).where((Seller.email == request.email) | (Seller.inn == request.inn))
    result = await session.execute(stmt)
    return result.scalars().first()


async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)):
    seller = Seller(
        email=request.email,
        password_hash=hash_password(request.password),
        role="seller",
        company_name=request.company_name,
        inn=request.inn,
        first_name=request.first_name,
        middle_name=request.middle_name,
        last_name=request.last_name,
        phone=request.phone
    )
    session.add(seller)
    await session.flush()

    access_token = create_access_token(str(seller.id), seller.role)
    refresh_token = create_refresh_token(str(seller.id), seller.role)

    decoded_refresh = decode_token(refresh_token)
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


async def login(request: LoginRequest, session: AsyncSession):
    stmt = select(Seller).where(Seller.email == request.email)
    result = await session.execute(stmt)
    seller = result.scalars().first()

    if not seller or not verify_password(request.password, seller.password_hash):
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


async def refresh_token(rt: Row | RowMapping, payload: dict, session: AsyncSession):
    rt.revoked = True
    session.add(rt)

    user_id = str(rt.seller_id)
    role = payload.get("role", "seller")
    new_access = create_access_token(user_id, role)
    new_refresh = create_refresh_token(user_id, role)

    decoded_new = decode_token(new_refresh)
    new_rt = RefreshToken(
        jti=decoded_new["jti"],
        seller_id=rt.seller_id,
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


async def logout(payload: dict, session: AsyncSession):
    jti = payload.get("jti")
    if jti:
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await session.execute(stmt)
        rt = result.scalars().first()
        if rt:
            rt.revoked = True
            session.add(rt)
            await session.commit()
    return
