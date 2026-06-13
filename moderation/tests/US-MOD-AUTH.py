import pytest
from uuid import uuid4
from httpx import AsyncClient
from src.models import Moderator
from shared.enums import UserRole
from src.services.auth_service import hash_password, token_service
from src.dependencies import get_current_user
from src.main import app
from src.schemas.moderator import ModeratorCreateRequest


@pytest.mark.asyncio
async def test_admin_can_access_moderators(client: AsyncClient):
    """Администратор (TEST_ADMIN) может получить список модераторов (200)."""
    response = await client.get("/api/v1/moderators")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total_count" in data
    emails = [m["email"] for m in data["items"]]
    assert "admin@example.com" in emails


@pytest.mark.asyncio
async def test_moderator_without_admin_role_gets_403(client: AsyncClient, db_session):
    """Обычный модератор не имеет доступа к /moderators -> 403."""
    mod = Moderator(
        id=uuid4(),
        email="mod@example.com",
        first_name="Mod",
        last_name="Test",
        password_hash=hash_password("password12"),
        role=UserRole.MODERATOR,
        is_active=True,
    )
    db_session.add(mod)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: mod
    try:
        response = await client.get("/api/v1/moderators")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_creates_moderator_and_appears_in_list(client: AsyncClient, db_session):
    """Админ создаёт модератора и видит его в списке."""
    new_email = f"newmod_{uuid4().hex[:8]}@example.com"
    payload = {
        "email": new_email,
        "password": "ValidPass123!",
        "first_name": "New",
        "last_name": "Moderator",
        "role": "MODERATOR",
    }
    response = await client.post("/api/v1/moderators", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["email"] == new_email
    assert created["role"] == "MODERATOR"

    list_response = await client.get("/api/v1/moderators")
    assert list_response.status_code == 200
    emails = [m["email"] for m in list_response.json()["items"]]
    assert new_email in emails


@pytest.mark.asyncio
async def test_created_moderator_can_login(client: AsyncClient, db_session):
    """Админ создаёт модератора, затем он может залогиниться."""
    new_email = f"loginmod_{uuid4().hex[:8]}@example.com"
    password = "StrongPass123"
    payload = {
        "email": new_email,
        "password": password,
        "first_name": "Login",
        "last_name": "Mod",
        "role": "MODERATOR",
    }
    create_resp = await client.post("/api/v1/moderators", json=payload)
    assert create_resp.status_code == 201

    login_payload = {"email": new_email, "password": password}
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "Bearer"
    assert tokens["user_id"] == create_resp.json()["id"]
