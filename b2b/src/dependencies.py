from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.seller import Seller
from src.database import get_session
from src.config import settings

from shared.exceptions import TokenInvalid, UserBlocked, Forbidden
from shared.security import TokenService
from shared.enums import UserRole


token_service = TokenService(
    secret=settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
    access_ttl_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_ttl_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


def get_token_service() -> TokenService:
    return token_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_token_payload(
        token: str = Depends(oauth2_scheme),
        ts: TokenService = Depends(get_token_service),
) -> dict:
    if not token:
        raise TokenInvalid(message="Missing access token")
    return ts.decode_token(token)


async def get_current_user_optional(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_session),
        ts: TokenService = Depends(get_token_service),
) -> Seller | None:
    if not token:
        return None
    try:
        payload = ts.decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = await session.get(Seller, user_id)
        if not user or not user.is_active:
            return None
        if payload.get("role") != user.role:
            return None
        return user
    except (TokenInvalid, TokenExpired):
        return None


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_session),
        ts: TokenService = Depends(get_token_service),
) -> Seller:
    if not token:
        raise TokenInvalid(message="Missing authorization token")

    payload = ts.decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalid(message="Token missing 'sub' claim")

    user = await session.get(Seller, user_id)
    if not user:
        raise TokenInvalid()
    if not user.is_active:
        raise UserBlocked()

    if user.role != UserRole.SELLER.value or payload.get("role") != user.role:
        raise Forbidden(message="Access denied: seller role required")

    return user


def require_service_key(x_service_key: str | None = Header(default=None, alias="X-Service-Key")) -> str:
    if not x_service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Not authenticated"}
        )
    return x_service_key


def require_b2c_key(x_service_key: str = Depends(require_service_key)) -> None:
    if x_service_key != settings.B2C_TO_B2B_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid service key"},
        )


def require_moderation_key(x_service_key: str = Depends(require_service_key)) -> None:
    if x_service_key != settings.B2B_TO_MOD_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid service key"}
        )
