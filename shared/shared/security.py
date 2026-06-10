import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt, ExpiredSignatureError, JWTError
from passlib.context import CryptContext
from .exceptions import TokenExpired, TokenInvalid
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


class TokenService:
    def __init__(self, secret: str, algorithm: str, access_ttl_minutes: int, refresh_ttl_days: int):
        self.secret = secret
        self.algorithm = algorithm
        self.access_ttl_minutes = access_ttl_minutes
        self.refresh_ttl_days = refresh_ttl_days

    def create_access_token(self, sub: str, role: str) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_ttl_minutes)
        payload = {
            "sub": sub,
            "role": role,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, sub: str, role: str) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_ttl_days)
        payload = {
            "sub": sub,
            "role": role,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except ExpiredSignatureError:
            raise TokenExpired()
        except JWTError:
            raise TokenInvalid()
