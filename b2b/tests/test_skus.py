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
from src.schemas.sku import SKUResponse
from src.services.exceptions import ProductNotFound, ForbiddenOperation

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
def valid_sku_payload():
    return {
        "product_id": str(uuid4()),
        "name": "Test SKU",
        "price": 10000,
        "cost_price": 5000,
        "discount": 0,
        "image": "http://example.com/img.jpg",
        "characteristics": [{"name": "Color", "value": "Black"}]
    }

@pytest.mark.asyncio
async def test_first_sku_transitions_product_to_on_moderation(client, valid_sku_payload):
    with patch("src.services.sku_service.create_sku", new_callable=AsyncMock) as mock_create:
        sku_id = uuid4()
        expected = SKUResponse(
            id=sku_id,
            product_id=uuid4(),
            name=valid_sku_payload["name"],
            price=10000,
            cost_price=5000,
            discount=0,
            active_quantity=0,
            reserved_quantity=0,
            image=valid_sku_payload["image"],
            characteristics=[],
            images=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_create.return_value = expected
        response = await client.post("/api/v1/skus/create", json=valid_sku_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == valid_sku_payload["name"]
        called_seller_id = mock_create.call_args[0][1]
        assert called_seller_id == TEST_SELLER_ID

@pytest.mark.asyncio
async def test_second_sku_no_state_change(client, valid_sku_payload):
    with patch("src.services.sku_service.create_sku", new_callable=AsyncMock) as mock_create:
        sku_id = uuid4()
        expected = SKUResponse(
            id=sku_id,
            product_id=uuid4(),
            name=valid_sku_payload["name"],
            price=10000,
            cost_price=5000,
            discount=0,
            active_quantity=0,
            reserved_quantity=0,
            image=valid_sku_payload["image"],
            characteristics=[],
            images=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_create.return_value = expected
        response = await client.post("/api/v1/skus/create", json=valid_sku_payload)
        assert response.status_code == 201

@pytest.mark.asyncio
async def test_add_sku_to_hard_blocked_returns_403(client, valid_sku_payload):
    with patch("src.services.sku_service.create_sku", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = ForbiddenOperation("Cannot add SKU to hard-blocked product")
        response = await client.post("/api/v1/skus/create", json=valid_sku_payload)
        assert response.status_code == 403
        assert "hard-blocked" in response.text.lower()

@pytest.mark.asyncio
async def test_missing_image_returns_400(client, valid_sku_payload):
    payload = valid_sku_payload.copy()
    payload.pop("image")
    response = await client.post("/api/v1/skus/create", json=payload)
    assert response.status_code == 400
    assert "image" in response.text.lower()