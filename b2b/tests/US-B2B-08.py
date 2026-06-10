import pytest
from uuid import uuid4
from src.models import SKU, Category, Product, ProductStatus
from tests.conftest import TEST_SELLER_ID
from src.config import settings
import json

@pytest.fixture
async def skus(db_session):
    cat = Category(id=uuid4(), name="Cat")
    db_session.add(cat)
    prod = Product(
        id=uuid4(), seller_id=TEST_SELLER_ID, category_id=cat.id,
        title="Test", slug="test", description="desc", status=ProductStatus.MODERATED
    )
    db_session.add(prod)
    sku1 = SKU(
        id=uuid4(), product_id=prod.id, name="SKU1", price=1000, active_quantity=10,
        reserved_quantity=0, stock_quantity=10, cost_price=500
    )
    sku2 = SKU(
        id=uuid4(), product_id=prod.id, name="SKU2", price=2000, active_quantity=5,
        reserved_quantity=0, stock_quantity=5, cost_price=800
    )
    db_session.add_all([sku1, sku2])
    await db_session.commit()
    return [sku1, sku2]

@pytest.mark.asyncio
async def test_reserve_all_skus_succeeds(client, skus, db_session):
    order_id = uuid4()
    payload = {
        "idempotency_key": str(uuid4()),
        "order_id": str(order_id),
        "items": [
            {"sku_id": str(skus[0].id), "quantity": 2},
            {"sku_id": str(skus[1].id), "quantity": 1}
        ]
    }
    response = await client.post(
        "/api/v1/inventory/reserve",
        json=payload,
        headers={"X-Service-Key": settings.B2B_TO_B2C_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == str(order_id)
    assert data["status"] == "RESERVED"
    await db_session.refresh(skus[0])
    await db_session.refresh(skus[1])
    assert skus[0].active_quantity == 8
    assert skus[0].reserved_quantity == 2
    assert skus[1].active_quantity == 4
    assert skus[1].reserved_quantity == 1

@pytest.mark.asyncio
async def test_partial_insufficient_stock_returns_409_all_rollback(client, skus):
    payload = {
        "idempotency_key": str(uuid4()),
        "order_id": str(uuid4()),
        "items": [
            {"sku_id": str(skus[0].id), "quantity": 2},
            {"sku_id": str(skus[1].id), "quantity": 10}
        ]
    }
    response = await client.post(
        "/api/v1/inventory/reserve",
        json=payload,
        headers={"X-Service-Key": settings.B2B_TO_B2C_KEY}
    )
    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "INSUFFICIENT_STOCK"
    assert skus[0].active_quantity == 10
    assert skus[0].reserved_quantity == 0
    assert skus[1].active_quantity == 5
    assert skus[1].reserved_quantity == 0

@pytest.mark.asyncio
async def test_idempotent_reserve_returns_200_without_double_deduction(client, skus):
    key = str(uuid4())
    order_id = uuid4()
    payload = {
        "idempotency_key": key,
        "order_id": str(order_id),
        "items": [{"sku_id": str(skus[0].id), "quantity": 1}]
    }
    resp1 = await client.post("/api/v1/inventory/reserve", json=payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/inventory/reserve", json=payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    assert resp2.status_code == 200
    assert skus[0].active_quantity == 9
    assert skus[0].reserved_quantity == 1


@pytest.mark.asyncio
async def test_sku_out_of_stock_event_emitted(httpx_mock, client, skus, db_session):
    skus[0].active_quantity = 1
    await db_session.commit()

    httpx_mock.add_response(
        method="POST",
        url=f"{settings.B2C_URL}/api/v1/b2b/events",
        status_code=200
    )

    payload = {
        "idempotency_key": str(uuid4()),
        "order_id": str(uuid4()),
        "items": [{"sku_id": str(skus[0].id), "quantity": 1}]
    }
    response = await client.post(
        "/api/v1/inventory/reserve",
        json=payload,
        headers={"X-Service-Key": settings.B2B_TO_B2C_KEY}
    )
    assert response.status_code == 200

    request = httpx_mock.get_request()
    assert request is not None
    assert request.url == f"{settings.B2C_URL}/api/v1/b2b/events"
    assert request.headers["X-Service-Key"] == settings.B2B_TO_B2C_KEY

    json_body = json.loads(request.content)
    assert json_body["event_type"] == "SKU_OUT_OF_STOCK"
    assert "idempotency_key" in json_body
    assert json_body["occurred_at"] is not None
    payload_data = json_body["payload"]
    assert payload_data["sku_id"] == str(skus[0].id)
    assert payload_data["product_id"] == str(skus[0].product_id)
    assert payload_data["available_quantity"] == 0

@pytest.mark.asyncio
async def test_unreserve_restores_quantities(client, skus):
    order_id = uuid4()
    key = str(uuid4())
    reserve_payload = {
        "idempotency_key": key,
        "order_id": str(order_id),
        "items": [{"sku_id": str(skus[0].id), "quantity": 2}]
    }
    await client.post("/api/v1/inventory/reserve", json=reserve_payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    unreserve_payload = {
        "order_id": str(order_id),
        "items": [{"sku_id": str(skus[0].id), "quantity": 2}]
    }
    response = await client.post("/api/v1/inventory/unreserve", json=unreserve_payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UNRESERVED"
    assert data["order_id"] == str(order_id)
    assert skus[0].active_quantity == 10
    assert skus[0].reserved_quantity == 0

@pytest.mark.asyncio
async def test_unreserve_idempotent(client, skus):
    order_id = uuid4()
    key = str(uuid4())
    reserve_payload = {
        "idempotency_key": key,
        "order_id": str(order_id),
        "items": [{"sku_id": str(skus[0].id), "quantity": 1}]
    }
    await client.post("/api/v1/inventory/reserve", json=reserve_payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    unreserve_payload = {
        "order_id": str(order_id),
        "items": [{"sku_id": str(skus[0].id), "quantity": 1}]
    }
    resp1 = await client.post("/api/v1/inventory/unreserve", json=unreserve_payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/inventory/unreserve", json=unreserve_payload, headers={"X-Service-Key": settings.B2B_TO_B2C_KEY})
    assert resp2.status_code == 200
    assert skus[0].active_quantity == 10
    assert skus[0].reserved_quantity == 0