import pytest
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user
from src.models import Seller, ProductStatus, Category, Product

from tests.conftest import TEST_SELLER_ID


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


@pytest.mark.asyncio
async def test_create_product_201(client, db_session, valid_payload):
    category_id = uuid4()
    await _create_category(db_session, category_id)
    valid_payload["category_id"] = str(category_id)

    response = await client.post("/api/v1/products", json=valid_payload)
    if response.status_code != 201:
        print(f"ERROR {response.status_code}: {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "CREATED"

    product_id = data["id"]
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    product = result.scalar_one()
    assert product.status == ProductStatus.CREATED
    assert product.seller_id == TEST_SELLER_ID
    assert product.category_id == category_id
    assert product.title == valid_payload["title"]


@pytest.mark.asyncio
async def test_seller_id_from_jwt(client, db_session, valid_payload):
    category_id = uuid4()
    await _create_category(db_session, category_id)
    valid_payload["category_id"] = str(category_id)

    response = await client.post("/api/v1/products", json=valid_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["seller_id"] == str(TEST_SELLER_ID)

    product_id = data["id"]
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    product = result.scalar_one()
    assert product.seller_id == TEST_SELLER_ID


@pytest.mark.asyncio
async def test_invalid_category_id_400(client, db_session, valid_payload):
    response = await client.post("/api/v1/products", json=valid_payload)
    assert response.status_code == 400
    assert "category not found" in response.text.lower()

    stmt = select(Product).where(Product.title == valid_payload["title"])
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_missing_images_400(client, valid_payload):
    payload = valid_payload.copy()
    payload.pop("images")
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    assert "image" in response.text.lower()


@pytest.mark.asyncio
async def test_missing_category_400(client, valid_payload):
    payload = valid_payload.copy()
    payload.pop("category_id")
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    assert "category" in response.text.lower()

# Доп тесты на кастом ошибки

@pytest.mark.asyncio
async def test_create_product_empty_title_returns_400(client, valid_payload):
    """Пустой title возвращает 400 с кодом INVALID_REQUEST."""
    payload = valid_payload.copy()
    payload["title"] = ""
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "title is required"


@pytest.mark.asyncio
async def test_create_product_title_too_long_returns_400(client, valid_payload):
    """title длиннее 255 символов возвращает 400."""
    payload = valid_payload.copy()
    payload["title"] = "a" * 256
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "title must be 1-255 characters"


@pytest.mark.asyncio
async def test_create_product_nonexistent_category_returns_400(client, valid_payload):
    """category_id не существует (валидный UUID, но нет в БД) возвращает 400."""
    payload = valid_payload.copy()
    payload["category_id"] = str(uuid4())
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "Category not found"


@pytest.mark.asyncio
async def test_create_product_missing_images_returns_400_format(client, valid_payload):
    """Отсутствие изображений возвращает 400 с точным сообщением."""
    payload = valid_payload.copy()
    del payload["images"]
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "At least one image is required"


@pytest.mark.asyncio
async def test_create_product_invalid_category_uuid_returns_400(client, valid_payload):
    """Невалидный UUID в category_id возвращает 400."""
    payload = valid_payload.copy()
    payload["category_id"] = "not-a-valid-uuid"
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "category_id must be a valid UUID"