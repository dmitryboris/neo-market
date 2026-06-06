from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from src.security import decode_token
from src.models.seller import Seller
from src.database import get_session
from src.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

async def get_current_user_optional(
    token: str | None = Depends(optional_oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Seller | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = await session.get(Seller, user_id)
    if not user or not user.is_active:
        return None
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Seller:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Невалидный токен"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Невалидный токен"},
        )
    user = await session.get(Seller, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Пользователь не найден или заблокирован"},
        )
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