import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from src.main import app
from src.models import Buyer, Order, OrderItem, OrderStatus
from src.database import get_session
from src.config import settings
from tests.conftest import TEST_BUYER_ID, create_access_token

@pytest.fixture
async def auth_client(client, db_session):
    buyer = await db_session.get(Buyer, TEST_BUYER_ID)
    token = create_access_token(str(buyer.id), "BUYER")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, buyer

@pytest.fixture
def mock_b2b_sku():
    with patch("src.services.b2b_client.get_sku", new_callable=AsyncMock) as mock_sku:
        yield mock_sku

@pytest.fixture
def mock_b2b_reserve():
    with patch("src.services.b2b_client.reserve_skus", new_callable=AsyncMock) as mock_reserve:
        yield mock_reserve

@pytest.mark.asyncio
async def test_checkout_creates_paid_order_with_fixed_prices(
    auth_client, db_session, mock_b2b_sku, mock_b2b_reserve
):
    client, buyer = auth_client
    sku_id = uuid4()
    product_id = uuid4()
    mock_b2b_sku.return_value = {
        "product_id": product_id,
        "active_quantity": 10,
        "price": 1000,
        "name": "Test SKU",
        "product_title": "Test Product"
    }
    mock_b2b_reserve.return_value = {"reserved": True}

    payload = {
        "idempotency_key": str(uuid4()),
        "items": [{"sku_id": str(sku_id), "quantity": 2}],
        "delivery_address": "Moscow, Red Square 1"
    }
    headers = {"Idempotency-Key": payload["idempotency_key"]}
    response = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PAID"
    assert data["total_amount"] == 2000
    assert len(data["items"]) == 1
    assert data["items"][0]["unit_price"] == 1000
    assert data["items"][0]["line_total"] == 2000

    # Проверка БД
    order = await db_session.execute(select(Order).where(Order.id == uuid.UUID(data["id"])))
    order = order.scalar_one()
    assert order.total_amount == 2000
    assert order.status == OrderStatus.PAID
    items = await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = items.scalars().all()
    assert len(items) == 1
    assert items[0].unit_price == 1000

@pytest.mark.asyncio
async def test_partial_reserve_failure_returns_409(
    auth_client, db_session, mock_b2b_sku, mock_b2b_reserve
):
    client, buyer = auth_client
    sku1 = uuid4()
    sku2 = uuid4()
    mock_b2b_sku.side_effect = lambda sku_id: {
        sku1: {"product_id": uuid4(), "active_quantity": 2, "price": 1000, "name": "SKU1"},
        sku2: {"product_id": uuid4(), "active_quantity": 0, "price": 2000, "name": "SKU2"},
    }[sku_id]

    mock_b2b_reserve.side_effect = HTTPException(
        status_code=409,
        detail={"failed_items": [{"sku_id": str(sku2), "reason": "OUT_OF_STOCK"}]}
    )

    payload = {
        "idempotency_key": str(uuid4()),
        "items": [
            {"sku_id": str(sku1), "quantity": 1},
            {"sku_id": str(sku2), "quantity": 1}
        ]
    }
    headers = {"Idempotency-Key": payload["idempotency_key"]}
    response = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "RESERVE_FAILED"
    assert "failed_items" in response.json()["details"]

@pytest.mark.asyncio
async def test_idempotency_returns_existing_order(
    auth_client, db_session, mock_b2b_sku, mock_b2b_reserve
):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b_sku.return_value = {"product_id": uuid4(), "active_quantity": 10, "price": 1000, "name": "Test"}
    mock_b2b_reserve.return_value = {"reserved": True}

    key = str(uuid4())
    payload = {
        "idempotency_key": key,
        "items": [{"sku_id": str(sku_id), "quantity": 1}]
    }
    headers = {"Idempotency-Key": key}
    resp1 = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp2.status_code == 201
    assert resp2.json()["id"] == resp1.json()["id"]

@pytest.mark.asyncio
async def test_b2b_unavailable_returns_503(
    auth_client, db_session, mock_b2b_sku, mock_b2b_reserve
):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b_sku.side_effect = HTTPException(
        status_code=503,
        detail={"code": "B2B_UNAVAILABLE", "message": "Service unavailable"}
    )
    payload = {
        "idempotency_key": str(uuid4()),
        "items": [{"sku_id": str(sku_id), "quantity": 1}]
    }
    headers = {"Idempotency-Key": payload["idempotency_key"]}
    response = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert response.status_code == 503
    assert response.json()["code"] == "B2B_UNAVAILABLE"