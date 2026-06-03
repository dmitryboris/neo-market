import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user
from src.models import Seller, ProductStatus, Category, Product


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
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def valid_payload():
    return {
        "category_id": str(uuid4()),
        "title": f"Test Product {uuid4()}",
        "slug": f"test-product-{uuid4().hex[:8]}",
        "description": "Test desc",
        "images": [{"url": "http://ex.com/i.jpg", "ordering": 0}],
        "characteristics": [{"name": "Brand", "value": "X"}]
    }


async def _create_category(session, category_id):
    cat = Category(id=category_id, name="Test Category")
    session.add(cat)
    await session.flush()


@pytest.fixture
async def seller(db_session):
    """Создаёт тестового продавца для тестов SKU (отдельный от TEST_SELLER)."""
    seller_id = uuid4()
    seller = Seller(
        id=seller_id,
        email=f"seller_{uuid4()}@test.com",
        first_name="SKU",
        last_name="Tester",
        company_name="SKU Test Co",
        inn=str(uuid4().int)[:12],
        password_hash="fake",
        role="seller"
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest.fixture
async def product(db_session, seller):
    """Создаёт товар со статусом CREATED для тестов SKU."""
    category_id = uuid4()
    cat = Category(id=category_id, name="Test Category")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=seller.id,
        category_id=category_id,
        title="Test Product {uuid4()}",
        slug=f"test-product-{uuid4().hex[:8]}",
        description="Test description",
        images=[{"url": "http://ex.com/i.jpg", "ordering": 0}],
        characteristics=[{"name": "Brand", "value": "X"}],
        status=ProductStatus.CREATED
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod