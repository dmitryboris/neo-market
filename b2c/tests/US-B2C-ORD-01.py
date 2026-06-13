import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, HTTPStatusError
from sqlalchemy import select
from src.models import Order, OrderItem, Address, PaymentMethod, Cart, CartItem, Buyer, IdempotencyRecord
from src.models.order import OrderStatus
from tests.conftest import TEST_BUYER_ID, create_access_token


@pytest.fixture
async def auth_client(client, db_session):
    buyer = await db_session.get(Buyer, TEST_BUYER_ID)
    token = create_access_token(str(buyer.id), "BUYER")
    client.headers["Authorization"] = f"Bearer {token}"
    return client, buyer


@pytest.fixture
async def test_address(db_session):
    address = Address(
        buyer_id=TEST_BUYER_ID,
        country="Russia",
        city="Moscow",
        street="Tverskaya",
        building="10",
        postal_code="125009",
        is_default=True,
    )
    db_session.add(address)
    await db_session.commit()
    return address


@pytest.fixture
async def test_payment_method(db_session):
    pm = PaymentMethod(
        buyer_id=TEST_BUYER_ID,
        brand="MASTERCARD",
        last4="1234",
        exp_year=2030,
        exp_month=12,
        is_default=True,
        type = "CARD"
    )
    db_session.add(pm)
    await db_session.commit()
    return pm


@pytest.fixture
async def cart_with_sku(db_session):
    cart = Cart(user_id=TEST_BUYER_ID)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    product_id = uuid4()
    item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=product_id, quantity=2)
    db_session.add(item)
    await db_session.commit()
    return cart, sku_id, product_id


@pytest.fixture
async def cart_with_two_skus(db_session):
    cart = Cart(user_id=TEST_BUYER_ID)
    db_session.add(cart)
    await db_session.flush()
    sku1 = uuid4()
    sku2 = uuid4()
    prod1 = uuid4()
    prod2 = uuid4()
    db_session.add_all([
        CartItem(cart_id=cart.id, sku_id=sku1, product_id=prod1, quantity=1),
        CartItem(cart_id=cart.id, sku_id=sku2, product_id=prod2, quantity=1),
    ])
    await db_session.commit()
    return cart, [(sku1, prod1), (sku2, prod2)]


@pytest.mark.asyncio
async def test_checkout_creates_paid_order_with_fixed_prices(
    auth_client, db_session, test_address, test_payment_method, cart_with_sku
):
    client, buyer = auth_client
    cart, sku_id, product_id = cart_with_sku

    payload = {
        "address_id": str(test_address.id),
        "payment_method_id": str(test_payment_method.id),
        "comment": "Test order"
    }
    idempotency_key = str(uuid4())
    headers = {"Idempotency-Key": idempotency_key}

    with patch("src.services.cart_service.batch_get_products", new_callable=AsyncMock) as mock_batch, \
         patch("src.services.order_service.reserve_skus", new_callable=AsyncMock) as mock_reserve:

        mock_batch.return_value = {
            product_id: {
                "status": "MODERATED",
                "title": "Test Product",
                "skus": {
                    sku_id: {
                        "price": 1000,
                        "active_quantity": 10,
                        "name": "Test SKU",
                        "sku_code": "SKU001"
                    }
                }
            }
        }
        mock_reserve.return_value = {"reserved": True, "items": []}

        response = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()

        assert data["status"] == "PAID"
        assert data["total"] == 2000
        assert data["subtotal"] == 2000
        assert len(data["items"]) == 1
        assert data["items"][0]["unit_price"] == 1000
        assert data["items"][0]["line_total"] == 2000
        assert data["address"]["id"] == str(test_address.id)
        assert data["payment_method"]["id"] == str(test_payment_method.id)

        order = await db_session.execute(select(Order).where(Order.id == UUID(data["id"])))
        order = order.scalar_one()
        assert order.total_amount == 2000
        assert order.status == OrderStatus.PAID
        items = await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        items = items.scalars().all()
        assert len(items) == 1
        assert items[0].unit_price == 1000
        assert items[0].quantity == 2


@pytest.mark.asyncio
async def test_idempotency_returns_existing_order(
    auth_client, db_session, test_address, test_payment_method, cart_with_sku
):
    client, buyer = auth_client
    cart, sku_id, product_id = cart_with_sku

    idempotency_key = str(uuid4())
    payload = {
        "address_id": str(test_address.id),
        "payment_method_id": str(test_payment_method.id),
    }
    headers = {"Idempotency-Key": idempotency_key}

    with patch("src.services.cart_service.batch_get_products", new_callable=AsyncMock) as mock_batch, \
         patch("src.services.order_service.reserve_skus", new_callable=AsyncMock) as mock_reserve, \
         patch("src.services.cart_service.get_sku", new_callable=AsyncMock) as mock_sku:

        mock_batch.return_value = {
            product_id: {
                "status": "MODERATED",
                "title": "Product",
                "skus": {sku_id: {"price": 1000, "active_quantity": 10, "name": "SKU"}}
            }
        }
        mock_reserve.return_value = {"reserved": True}
        mock_sku.return_value = {
            "product_id": product_id,
            "active_quantity": 10,
            "price": 1000,
            "name": "SKU"
        }

        resp1 = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert resp2.status_code == 201
        assert resp2.json()["id"] == resp1.json()["id"]

        assert mock_reserve.await_count == 1


@pytest.mark.asyncio
async def test_partial_reserve_failure_returns_409(
    auth_client, db_session, test_address, test_payment_method, cart_with_two_skus
):
    client, buyer = auth_client
    cart, skus = cart_with_two_skus
    sku1, prod1 = skus[0]
    sku2, prod2 = skus[1]

    payload = {
        "address_id": str(test_address.id),
        "payment_method_id": str(test_payment_method.id),
    }
    idempotency_key = str(uuid4())
    headers = {"Idempotency-Key": idempotency_key}

    with patch("src.services.cart_service.batch_get_products", new_callable=AsyncMock) as mock_batch, \
         patch("src.services.order_service.reserve_skus", new_callable=AsyncMock) as mock_reserve:

        mock_batch.return_value = {
            prod1: {
                "status": "MODERATED",
                "title": "Product 1",
                "skus": {sku1: {"price": 1000, "active_quantity": 10, "name": "SKU1"}}
            },
            prod2: {
                "status": "MODERATED",
                "title": "Product 2",
                "skus": {sku2: {"price": 2000, "active_quantity": 0, "name": "SKU2"}}
            }
        }
        mock_reserve.side_effect = HTTPStatusError(
            message="Conflict",
            request=None,
            response=AsyncMock(status_code=409, json=lambda: {
                "reserved": False,
                "failed_items": [{"sku_id": str(sku2), "requested": 1, "available": 0, "reason": "OUT_OF_STOCK"}]
            })
        )

        response = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert response.status_code == 409
        error = response.json()
        assert error["code"] == "RESERVE_FAILED"
        assert "failed_items" in error["details"]
        assert error["details"]["failed_items"][0]["sku_id"] == str(sku2)
        assert error["details"]["failed_items"][0]["reason"] == "OUT_OF_STOCK"

        record = await db_session.get(IdempotencyRecord, UUID(idempotency_key))
        assert record is None


@pytest.mark.asyncio
async def test_b2b_unavailable_returns_503(
    auth_client, db_session, test_address, test_payment_method, cart_with_sku
):
    client, buyer = auth_client
    cart, sku_id, product_id = cart_with_sku

    payload = {
        "address_id": str(test_address.id),
        "payment_method_id": str(test_payment_method.id),
    }
    idempotency_key = str(uuid4())
    headers = {"Idempotency-Key": idempotency_key}

    with patch("src.services.cart_service.batch_get_products", new_callable=AsyncMock) as mock_batch, \
         patch("src.services.b2b_client._request", new_callable=AsyncMock) as mock_reserve:

        mock_batch.return_value = {
            product_id: {
                "status": "MODERATED",
                "title": "Product",
                "skus": {sku_id: {"price": 1000, "active_quantity": 10, "name": "SKU"}}
            }
        }
        mock_reserve.side_effect = HTTPStatusError(
            message="Service Unavailable",
            request=None,
            response=AsyncMock(status_code=503, json=lambda: {"code": "B2B_UNAVAILABLE", "message": "Service unavailable"})
        )

        response = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert response.status_code == 503
        error = response.json()
        assert error["code"] == "B2B_UNAVAILABLE"

        record = await db_session.get(IdempotencyRecord, UUID(idempotency_key))
        assert record is None