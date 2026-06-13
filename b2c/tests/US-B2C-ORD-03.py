import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, HTTPStatusError
from sqlalchemy import select
from src.models import Order, OrderItem as OrderItemModel, Address, PaymentMethod, Cart, CartItem, Buyer, IdempotencyRecord
from src.models.order import OrderStatus
from tests.conftest import TEST_BUYER_ID, create_access_token
from src.services.exceptions import B2BUnavailable

@pytest.fixture
async def paid_order(db_session, test_address, test_payment_method):
    order = Order(
        user_id=TEST_BUYER_ID,
        status=OrderStatus.PAID,
        total_amount=1000,
        address_id=test_address.id,
        payment_method_id=test_payment_method.id,
    )

    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItemModel(
            order_id=order.id,
            sku_id=uuid4(),
            product_id=uuid4(),
            product_title="Product",
            sku_name="SKU",
            quantity=2,
            unit_price=500,
            line_total=1000,
        )
    )

    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_cancel_paid_order_transitions_to_cancelled(
    auth_client,
    paid_order,
):
    client, _ = auth_client

    with patch(
        "src.services.order_service.unreserve_skus",
        new_callable=AsyncMock,
    ) as mock_unreserve:

        mock_unreserve.return_value = {
            "unreserved": True
        }

        response = await client.post(
            f"/api/v1/orders/{paid_order.id}/cancel"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(paid_order.id)
    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_unreserve_failure_transitions_to_cancel_pending(
    auth_client,
    paid_order,
):
    client, _ = auth_client

    with patch(
        "src.services.order_service.unreserve_skus",
        new_callable=AsyncMock,
    ) as mock_unreserve:

        mock_unreserve.side_effect = B2BUnavailable()

        response = await client.post(
            f"/api/v1/orders/{paid_order.id}/cancel"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CANCEL_PENDING"


@pytest.mark.asyncio
async def test_cancel_delivered_order_returns_409(
    auth_client,
    db_session,
    test_address,
    test_payment_method,
):
    client, _ = auth_client

    order = Order(
        user_id=TEST_BUYER_ID,
        status=OrderStatus.DELIVERED,
        total_amount=1000,
        address_id=test_address.id,
        payment_method_id=test_payment_method.id,
    )

    db_session.add(order)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/orders/{order.id}/cancel"
    )

    assert response.status_code == 409

    data = response.json()

    assert data["code"] == "CANCEL_NOT_ALLOWED"
    assert data["details"]["current_status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_other_user_order_returns_404(
    auth_client,
    db_session,
    test_address,
    test_payment_method,
    another_buyer
):
    client, _ = auth_client

    order = Order(
        user_id=another_buyer.id,
        status=OrderStatus.PAID,
        total_amount=1000,
        address_id=test_address.id,
        payment_method_id=test_payment_method.id,
    )

    db_session.add(order)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/orders/{order.id}/cancel"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ORDER_NOT_FOUND"