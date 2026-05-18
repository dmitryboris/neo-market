import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import get_session
from src.dependencies import get_current_user
from src.models.seller import Seller
from src.models.product import ProductStatus
from src.schemas.product import ProductResponse
from src.services.exceptions import CategoryNotFound

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

async def override_get_session():
    yield AsyncMock()

async def override_get_current_user():
    return TEST_SELLER

app.dependency_overrides[get_session] = override_get_session
app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def valid_payload():
    return {
        "category_id": str(uuid4()),
        "title": "Test Product",
        "description": "Test desc",
        "images": [{"url": "http://ex.com/i.jpg", "ordering": 0}],
        "characteristics": [{"name": "Brand", "value": "X"}]
    }

@pytest.mark.asyncio
async def test_create_product_201(client, valid_payload):
    with patch("src.services.product_service.create_product", new_callable=AsyncMock) as mock:
        product_id = uuid4()
        expected = ProductResponse(
            id=product_id,
            seller_id=TEST_SELLER_ID,
            category_id=uuid4(),
            title=valid_payload["title"],
            description=valid_payload["description"],
            status=ProductStatus.CREATED,
            images=[],
            characteristics=[],
            skus=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock.return_value = expected
        response = await client.post("/api/v1/products", json=valid_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "CREATED"
        assert data["skus"] == []

@pytest.mark.asyncio
async def test_seller_id_from_jwt(client, valid_payload):
    with patch("src.services.product_service.create_product", new_callable=AsyncMock) as mock:
        product_id = uuid4()
        expected = ProductResponse(
            id=product_id,
            seller_id=TEST_SELLER_ID,
            category_id=uuid4(),
            title=valid_payload["title"],
            description=valid_payload["description"],
            status=ProductStatus.CREATED,
            images=[],
            characteristics=[],
            skus=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock.return_value = expected
        response = await client.post("/api/v1/products", json=valid_payload)
        assert response.status_code == 201
        assert response.json()["seller_id"] == str(TEST_SELLER_ID)

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

@pytest.mark.asyncio
async def test_invalid_category_id_400(client, valid_payload):
    with patch("src.services.product_service.create_product", new_callable=AsyncMock) as mock:
        mock.side_effect = CategoryNotFound("Category not found")
        response = await client.post("/api/v1/products", json=valid_payload)
        assert response.status_code == 400
        assert "category not found" in response.text.lower()