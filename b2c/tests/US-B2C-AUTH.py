import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from src.models import Buyer, RefreshToken, RefreshBlacklist
from shared.security import TokenService
from src.config import settings

token_service = TokenService(
    secret=settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
    access_ttl_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_ttl_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


@pytest.fixture
async def registered_buyer(client: AsyncClient, db_session):
    data = {
        "email": "buyer@test.com",
        "password": "Password123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1234567890",
    }
    resp = await client.post("/api/v1/auth/register", json=data)
    assert resp.status_code == 201
    body = resp.json()
    return {
        "email": data["email"],
        "password": data["password"],
        "user_id": body["user_id"],
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
    }


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session):
    data = {
        "email": "new@example.com",
        "password": "SecurePass123",
        "first_name": "Alice",
        "last_name": "Smith",
        "phone": "+79991112233",
    }
    resp = await client.post("/api/v1/auth/register", json=data)
    assert resp.status_code == 201
    json_resp = resp.json()
    assert "user_id" in json_resp
    assert "access_token" in json_resp
    assert "refresh_token" in json_resp
    assert json_resp["token_type"] == "Bearer"
    assert json_resp["expires_in"] == 3600

    stmt = select(Buyer).where(Buyer.email == data["email"])
    buyer = (await db_session.execute(stmt)).scalar_one_or_none()
    assert buyer is not None
    assert buyer.first_name == "Alice"
    assert buyer.role.lower() == "buyer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, registered_buyer):
    data = {
        "email": registered_buyer["email"],
        "password": "AnotherPass",
        "first_name": "Jane",
        "last_name": "Doe",
    }
    resp = await client.post("/api/v1/auth/register", json=data)
    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, registered_buyer):
    data = {
        "email": registered_buyer["email"],
        "password": registered_buyer["password"],
    }
    resp = await client.post("/api/v1/auth/login", json=data)
    assert resp.status_code == 200
    json_resp = resp.json()
    assert json_resp["user_id"] == registered_buyer["user_id"]
    assert "access_token" in json_resp
    assert "refresh_token" in json_resp


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, registered_buyer):
    data = {
        "email": registered_buyer["email"],
        "password": "WrongPass",
    }
    resp = await client.post("/api/v1/auth/login", json=data)
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, registered_buyer, db_session):
    old_refresh = registered_buyer["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    json_resp = resp.json()
    new_refresh = json_resp["refresh_token"]
    assert new_refresh != old_refresh

    payload_old = token_service.decode_token(old_refresh)
    stmt = select(RefreshBlacklist).where(RefreshBlacklist.jti == payload_old["jti"])
    blacklisted = (await db_session.execute(stmt)).scalar_one_or_none()
    assert blacklisted is not None


@pytest.mark.asyncio
async def test_refresh_twice_fails(client: AsyncClient, registered_buyer):
    refresh = registered_buyer["refresh_token"]
    resp1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp2.status_code == 401
    assert resp2.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_refresh_expired(client: AsyncClient, registered_buyer, db_session):
    refresh = registered_buyer["refresh_token"]
    payload = token_service.decode_token(refresh)
    stmt = select(RefreshToken).where(RefreshToken.jti == payload["jti"])
    rt = (await db_session.execute(stmt)).scalar_one()
    rt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401
    assert resp.json()["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.jwt.token"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, registered_buyer, db_session):
    headers = {"Authorization": f"Bearer {registered_buyer['access_token']}"}
    payload = {"refresh_token": registered_buyer["refresh_token"]}
    resp = await client.post("/api/v1/auth/logout", json=payload, headers=headers)
    assert resp.status_code == 204

    refresh_payload = token_service.decode_token(registered_buyer["refresh_token"])
    stmt = select(RefreshBlacklist).where(RefreshBlacklist.jti == refresh_payload["jti"])
    blacklisted = (await db_session.execute(stmt)).scalar_one_or_none()
    assert blacklisted is not None


@pytest.mark.asyncio
async def test_logout_without_access_token(client: AsyncClient, registered_buyer):
    payload = {"refresh_token": registered_buyer["refresh_token"]}
    resp = await client.post("/api/v1/auth/logout", json=payload)
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_logout_wrong_refresh(client: AsyncClient, registered_buyer):
    headers = {"Authorization": f"Bearer {registered_buyer['access_token']}"}
    payload = {"refresh_token": "some.wrong.token"}
    resp = await client.post("/api/v1/auth/logout", json=payload, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_logout_mismatched_user(client: AsyncClient, registered_buyer, db_session):
    data2 = {
        "email": "other@example.com",
        "password": "Password123",
        "first_name": "Other",
        "last_name": "User",
    }
    resp_reg = await client.post("/api/v1/auth/register", json=data2)
    assert resp_reg.status_code == 201
    other_refresh = resp_reg.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {registered_buyer['access_token']}"}
    payload = {"refresh_token": other_refresh}
    resp = await client.post("/api/v1/auth/logout", json=payload, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOKEN"
