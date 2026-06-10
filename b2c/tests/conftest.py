import pytest
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user, get_current_user_optional
from src.models import Buyer, Cart, CartItem
from src.services.auth_service import token_service
from src.services import cart_service
from unittest.mock import AsyncMock, patch

TEST_BUYER_ID = uuid4()
TEST_BUYER = Buyer(
    id=TEST_BUYER_ID,
    email="test@example.com",
    password_hash="$2b$12$...",  # фейковый хэш
    first_name="Test",
    last_name="Buyer",
    is_active=True,
)

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
    app.dependency_overrides[get_current_user] = lambda: None
    app.dependency_overrides[get_current_user_optional] = lambda: None
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

def create_access_token(user_id: str, role: str = "BUYER") -> str:
    return token_service.create_access_token(user_id, role)

@pytest.fixture
async def auth_client(client, db_session):
    # Создаём покупателя в БД (если не создан)
    buyer = await db_session.get(Buyer, TEST_BUYER_ID)
    if not buyer:
        buyer = TEST_BUYER
        db_session.add(buyer)
        await db_session.commit()
    token = create_access_token(str(buyer.id), "BUYER")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, buyer

@pytest.fixture
def mock_b2b():
    # Мокаем функции b2b_client, используемые в cart_service
    with patch("src.services.cart_service.check_sku", new_callable=AsyncMock) as mock_check, \
         patch("src.services.cart_service.batch_get_skus", new_callable=AsyncMock) as mock_batch:
        yield {"check": mock_check, "batch": mock_batch}