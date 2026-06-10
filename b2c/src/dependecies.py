from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.models.buyer import Buyer
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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_session),
        ts: TokenService = Depends(get_token_service),
) -> Buyer:
    if not token:
        raise TokenInvalid(message="Missing authorization token")

    payload = ts.decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalid(message="Token missing 'sub' claim")

    user = await session.get(Buyer, user_id)
    if not user:
        raise TokenInvalid()
    if not user.is_active:
        raise UserBlocked()

    if user.role != UserRole.BUYER.value or payload.get("role") != user.role:
        raise Forbidden(message="Access denied: buyer role required")

    return user
