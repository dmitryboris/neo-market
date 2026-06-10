import pytest
from uuid import uuid4
from unittest.mock import patch
from httpx import AsyncClient
from src.models import Buyer, Cart, CartItem
from src.services.cart_service import check_sku, batch_get_skus

@pytest.mark.asyncio
async def test_add_sku_increments_quantity_if_already_in_cart(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["check"].return_value = {"product_id": uuid4(), "active_quantity": 10, "price": 1000, "name": "Test"}
    resp1 = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 2})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 1
    assert data1["items"][0]["quantity"] == 2
    resp2 = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 3})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["quantity"] == 5

@pytest.mark.asyncio
async def test_get_cart_enriched_with_b2b_data(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["check"].return_value = {"product_id": uuid4(), "active_quantity": 10, "price": 1000, "name": "Test"}
    await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 2})
    mock_b2b["batch"].return_value = {
        str(sku_id): {"product_id": uuid4(), "name": "Test", "price": 1000, "active_quantity": 10, "is_visible": True}
    }
    resp = await client.get("/api/v1/cart")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["unit_price"] == 1000
    assert data["items"][0]["line_total"] == 2000
    assert data["subtotal"] == 2000

@pytest.mark.asyncio
async def test_unavailable_sku_shown_with_reason(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["check"].return_value = {"product_id": uuid4(), "active_quantity": 0, "price": 1000, "name": "Test"}
    await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 1})
    mock_b2b["batch"].return_value = {
        str(sku_id): {"product_id": uuid4(), "name": "Test", "price": 1000, "active_quantity": 0, "is_visible": True}
    }
    cart_resp = await client.get("/api/v1/cart")
    data = cart_resp.json()
    assert data["items"][0]["is_available"] is False
    assert data["items"][0]["available_quantity"] == 0

@pytest.mark.asyncio
async def test_guest_cart_merged_on_login(client, db_session, mock_b2b):
    session_id = str(uuid4())
    client.headers["X-Session-Id"] = session_id
    sku_id = uuid4()
    mock_b2b["check"].return_value = {"product_id": uuid4(), "active_quantity": 10, "price": 1000, "name": "Test"}
    await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 3})
    from src.models import Buyer
    buyer = Buyer(
        id=uuid4(),
        email="test_buyer@example.com",
        password_hash="fake_hash",
        first_name="Test",
        is_active=True,
    )
    db_session.add(buyer)
    await db_session.commit()
    login_data = {"email": "test_buyer@example.com", "password": "12345678"}
    with patch("src.routes.auth.verify_password", return_value=True):
        resp_login = await client.post("/api/v1/auth/login", json=login_data, headers={"X-Session-Id": session_id})
    assert resp_login.status_code == 200
    token = resp_login.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    del client.headers["X-Session-Id"]
    cart_resp = await client.get("/api/v1/cart")
    data = cart_resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3