import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user, get_current_user_optional
from src.models import Buyer
from unittest.mock import AsyncMock, patch
from src.services.auth_service import token_service

TEST_BUYER_ID = uuid4()
TEST_BUYER = Buyer(
    id=TEST_BUYER_ID,
    email="test_buyer@example.com",
    first_name="Test",
    last_name="Buyer",
    phone="+1234567890",
    password_hash="fake_hash",
    role="BUYER",
    is_active=True,
)

def create_access_token(user_id: str, role: str = "BUYER") -> str:
    return token_service.create_access_token(user_id, role)

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="session", autouse=True)
async def create_tables(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(TEST_BUYER)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_engine):
    async with test_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
        await conn.rollback()

@pytest.fixture(autouse=True)
def override_dependencies(db_session):
    async def _get_session():
        yield db_session

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_current_user] = lambda: TEST_BUYER
    app.dependency_overrides[get_current_user_optional] = lambda: TEST_BUYER
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client, db_session):
    buyer = TEST_BUYER
    token = create_access_token(str(buyer.id), "BUYER")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, buyer

@pytest.fixture
def mock_b2b():
    with patch("src.services.cart_service.get_sku", new_callable=AsyncMock) as mock_sku, \
         patch("src.services.cart_service.batch_get_products", new_callable=AsyncMock) as mock_batch:
        yield {"sku": mock_sku, "batch": mock_batch}