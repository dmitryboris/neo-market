import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user, get_current_user_optional
from src.models import Seller, Category


TEST_SELLER_ID = uuid4()
TEST_SELLER = Seller(
    id=TEST_SELLER_ID,
    email="test@example.com",
    first_name="Test",
    last_name="Seller",
    company_name="Test Company",
    inn="1111111111",
    password_hash="fake"
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
        session.add(TEST_SELLER)
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
    app.dependency_overrides[get_current_user] = lambda: TEST_SELLER
    app.dependency_overrides[get_current_user_optional] = lambda: TEST_SELLER
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
