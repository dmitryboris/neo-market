import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models.buyer import Buyer

from src.securiry import create_access_token, hash_password, create_refresh_token, verify_password


async def register_buyer(session: AsyncSession, request) -> dict:
    stmt = select(Buyer).where(Buyer.email == request.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise EmailAlreadyRegistered()

    buyer = Buyer(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        password_hash=hash_password(request.password),
    )
    session.add(buyer)
    await session.commit()
    await session.refresh(buyer)

    access_token = create_access_token(str(buyer.id))
    refresh_token = create_refresh_token(str(buyer.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def login_buyer(session: AsyncSession, request) -> dict:
    stmt = select(Buyer).where(Buyer.email == request.email)
    result = await session.execute(stmt)
    buyer = result.scalar_one_or_none()
    if not buyer or not verify_password(request.password, buyer.password_hash):
        raise InvalidCredentials()

    if not buyer.is_active:
        raise InactiveBuyer()

    access_token = create_access_token(str(buyer.id))
    refresh_token = create_refresh_token(str(buyer.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def refresh_access_token(refresh_token: str) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError
        buyer_id = payload["sub"]

        new_access = create_access_token(buyer_id)
        new_refresh = create_refresh_token(buyer_id)
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except jwt.ExpiredSignatureError:
        raise InvalidCredentials("Refresh token expired")
    except jwt.InvalidTokenError:
        raise InvalidCredentials("Invalid refresh token")
