import pytest
from uuid import uuid4
from src.models import Cart, CartItem
from src.services.exceptions import SkuNotFound
from src.services.cart_service import merge_carts_service, get_or_create_cart, add_cart_item_service
from src.models import CartItem as CartItemModel
from src.models import Buyer
from src.services.auth_service import hash_password
from sqlalchemy import select
from fastapi import HTTPException
from unittest.mock import patch


@pytest.mark.asyncio
async def test_add_sku_increments_quantity_if_already_in_cart(auth_client, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    product_id = uuid4()
    mock_b2b["sku"].return_value = {
        "product_id": product_id,
        "active_quantity": 10,
        "price": 1000,
        "name": "Test SKU",
        "sku_code": "TEST123"
    }
    mock_b2b["batch"].return_value = {
        product_id: {
            "status": "MODERATED",
            "title": "Test Product",
            "skus": {
                sku_id: {
                    "price": 1000,
                    "active_quantity": 10,
                    "name": "Test SKU",
                    "sku_code": "TEST123"
                }
            }
        }
    }
    resp1 = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 2})
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert len(data1["items"]) == 1
    assert data1["items"][0]["quantity"] == 2

    resp2 = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 3})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["quantity"] == 5


@pytest.mark.asyncio
async def test_add_cart_item_insufficient_stock(auth_client, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["sku"].return_value = {"active_quantity": 1, "product_id": uuid4(), "price": 1000, "name": "Test"}
    response = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 5})
    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_STOCK"

@pytest.mark.asyncio
async def test_add_cart_item_sku_not_found(auth_client, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["sku"].side_effect = SkuNotFound(f"SKU {sku_id} not found")
    response = await client.post("/api/v1/cart/items", json={"sku_id": str(sku_id), "quantity": 1})
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_cart_enriched_with_b2b_data(client, db_session, mock_b2b, auth_client):
    client, buyer = auth_client
    
    from src.models import Cart, CartItem
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    
    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        product_id=product_id,
        quantity=2
    )
    db_session.add(cart_item)
    await db_session.commit()
    
    mock_b2b["batch"].return_value = {
        product_id: {
            "status": "MODERATED",
            "title": "Test Product",
            "skus": {
                sku_id: {
                    "price": 1000,
                    "active_quantity": 10,
                    "name": "Test SKU",
                    "sku_code": "TEST123"
                }
            }
        }
    }
    
    resp = await client.get("/api/v1/cart")
    assert resp.status_code == 200
    data = resp.json()
    
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["sku_id"] == str(sku_id)
    assert item["product_id"] == str(product_id)
    assert item["name"] == "Test SKU"
    assert item["quantity"] == 2
    assert item["unit_price"] == 1000
    assert item["line_total"] == 2000
    assert item["available_quantity"] == 10
    assert item["is_available"] is True
    assert data["subtotal"] == 2000
    assert data["items_count"] == 2
    assert data["is_valid"] is True


@pytest.mark.asyncio
async def test_cart_sku_out_of_stock(auth_client, db_session, mock_b2b):
    client, buyer = auth_client

    from src.models import Cart, CartItem
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()

    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        product_id=product_id,
        quantity=1
    )
    db_session.add(cart_item)
    await db_session.commit()

    mock_b2b["batch"].return_value = {
        product_id: {
            "status": "MODERATED",
            "title": "Test Product",
            "skus": {
                sku_id: {
                    "price": 1000,
                    "active_quantity": 0,
                    "name": "Test SKU",
                }
            }
        }
    }

    resp = await client.get("/api/v1/cart")
    assert resp.status_code == 200
    data = resp.json()
    item = data["items"][0]
    assert item["is_available"] is False
    assert item["available_quantity"] == 0
    assert item["line_total"] == 0
    assert data["subtotal"] == 0
    assert data["is_valid"] is False


@pytest.mark.asyncio
async def test_update_cart_item_quantity(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    from src.models import Cart, CartItem
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=product_id, quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    mock_b2b["sku"].return_value = {
        "product_id": product_id,
        "active_quantity": 10,
        "price": 1000,
        "name": "Test SKU"
    }
    mock_b2b["batch"].return_value = {
        product_id: {
            "status": "MODERATED",
            "title": "Test Product",
            "skus": {
                sku_id: {
                    "price": 1000,
                    "active_quantity": 10,
                    "name": "Test SKU"
                }
            }
        }
    }

    resp = await client.patch(f"/api/v1/cart/items/{sku_id}", json={"quantity": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["quantity"] == 5
    assert data["items"][0]["line_total"] == 5000


@pytest.mark.asyncio
async def test_update_cart_item_insufficient_stock(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    cart_item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=uuid4(), quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    mock_b2b["sku"].return_value = {
        "active_quantity": 3,
        "product_id": uuid4(),
        "price": 1000,
        "name": "Test"
    }

    resp = await client.patch(f"/api/v1/cart/items/{sku_id}", json={"quantity": 5})
    assert resp.status_code == 409
    assert resp.json()["code"] == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_update_cart_item_not_found(auth_client, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    product_id = uuid4()
    mock_b2b["sku"].return_value = {
        "product_id": product_id,
        "active_quantity": 10,
        "price": 1000,
        "name": "Test SKU"
    }
    resp = await client.patch(f"/api/v1/cart/items/{sku_id}", json={"quantity": 1})
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND" 


@pytest.mark.asyncio
async def test_update_cart_item_invalid_quantity(auth_client):
    client, buyer = auth_client
    sku_id = uuid4()
    resp = await client.patch(f"/api/v1/cart/items/{sku_id}", json={"quantity": 0})
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_delete_cart_item_success(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=product_id, quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    mock_b2b["batch"].return_value = {}

    response = await client.delete(f"/api/v1/cart/items/{sku_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0
    assert data["items_count"] == 0

@pytest.mark.asyncio
async def test_delete_cart_item_nonexistent(auth_client, mock_b2b):
    client, buyer = auth_client
    sku_id = uuid4()
    mock_b2b["batch"].return_value = {}
    response = await client.delete(f"/api/v1/cart/items/{sku_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0

@pytest.mark.asyncio
async def test_clear_cart_success(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    cart_item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=uuid4(), quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    response = await client.delete("/api/v1/cart")
    assert response.status_code == 204
    get_response = await client.get("/api/v1/cart")
    assert get_response.status_code == 200
    data = get_response.json()
    assert len(data["items"]) == 0



@pytest.mark.asyncio
async def test_unavailable_sku_shown_with_reason(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()

    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        product_id=product_id,
        quantity=1,
    )
    db_session.add(cart_item)
    await db_session.commit()

    mock_b2b["batch"].return_value = {
        product_id: {
            "status": "MODERATED",
            "title": "Test Product",
            "skus": {
                sku_id: {
                    "price": 1000,
                    "active_quantity": 0,
                    "name": "Test SKU",
                }
            }
        }
    }

    resp = await client.post("/api/v1/cart/validate")
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_valid"] is False
    assert len(data["issues"]) == 1
    issue = data["issues"][0]
    assert issue["sku_id"] == str(sku_id)
    assert issue["type"] == "OUT_OF_STOCK"
    assert issue["message"] == "Нет в наличии"

    cart_resp = await client.get("/api/v1/cart")
    cart_data = cart_resp.json()
    assert cart_data["items"][0]["is_available"] is False
    assert cart_data["items"][0]["available_quantity"] == 0


@pytest.mark.asyncio
async def test_validation_all_reasons(auth_client, db_session, mock_b2b):
    client, buyer = auth_client
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()

    sku_out = uuid4()
    sku_blocked = uuid4()
    sku_deleted = uuid4()
    sku_reduced = uuid4()

    product_out = uuid4()
    product_blocked = uuid4()
    product_deleted = uuid4()
    product_reduced = uuid4()

    items = [
        CartItem(cart_id=cart.id, sku_id=sku_out, product_id=product_out, quantity=2),
        CartItem(cart_id=cart.id, sku_id=sku_blocked, product_id=product_blocked, quantity=1),
        CartItem(cart_id=cart.id, sku_id=sku_deleted, product_id=product_deleted, quantity=1),
        CartItem(cart_id=cart.id, sku_id=sku_reduced, product_id=product_reduced, quantity=5),
    ]
    db_session.add_all(items)
    await db_session.commit()

    mock_b2b["batch"].return_value = {
        product_out: {"status": "MODERATED", "title": "Product", "skus": {sku_out: {"active_quantity": 0, "price": 1000, "name": "Out"}}},
        product_blocked: {"status": "BLOCKED", "title": "Product", "skus": {sku_blocked: {"active_quantity": 10, "price": 1000, "name": "Blocked"}}},
        product_reduced: {"status": "MODERATED", "title": "Product", "skus": {sku_reduced: {"active_quantity": 2, "price": 1000, "name": "Reduced"}}},
    }

    resp = await client.post("/api/v1/cart/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False
    issues = {issue["type"]: issue for issue in data["issues"]}
    assert "OUT_OF_STOCK" in issues
    assert "PRODUCT_BLOCKED" in issues
    assert "PRODUCT_DELETED" in issues
    assert "QUANTITY_REDUCED" in issues

@pytest.mark.asyncio
async def test_merge_carts_service(db_session):
    buyer = Buyer(
        id=uuid4(),
        email="merge_test@example.com",
        password_hash=hash_password("12345678"),
        first_name="Merge",
        is_active=True,
    )
    db_session.add(buyer)
    await db_session.commit()
    user_id = buyer.id

    session_id = str(uuid4())
    
    guest_cart = await get_or_create_cart(db_session, session_id=session_id)
    product_id1 = uuid4()
    product_id2 = uuid4()
    sku_guest_only = uuid4()
    sku_conflict = uuid4()
    guest_item1 = CartItemModel(cart_id=guest_cart.id, sku_id=sku_guest_only, product_id=product_id1, quantity=3)
    guest_item2 = CartItemModel(cart_id=guest_cart.id, sku_id=sku_conflict, product_id=product_id2, quantity=5)
    db_session.add_all([guest_item1, guest_item2])
    await db_session.commit()
    
    user_cart = await get_or_create_cart(db_session, user_id=user_id)
    user_item = CartItemModel(cart_id=user_cart.id, sku_id=sku_conflict, product_id=product_id2, quantity=2)
    db_session.add(user_item)
    await db_session.commit()
    
    merged_cart = await merge_carts_service(db_session, user_id, session_id)
    
    items = await db_session.execute(select(CartItemModel).where(CartItemModel.cart_id == user_cart.id))
    items_list = items.scalars().all()
    assert len(items_list) == 2
    by_sku = {item.sku_id: item.quantity for item in items_list}
    assert by_sku[sku_guest_only] == 3
    assert by_sku[sku_conflict] == 5
    
    guest_cart_check = await db_session.get(Cart, guest_cart.id)
    assert guest_cart_check is None


@pytest.mark.asyncio
async def test_b2b_unavailable_returns_503(client, auth_client, db_session):
    client, buyer = auth_client
    from src.models import Cart, CartItem
    cart = Cart(user_id=buyer.id)
    db_session.add(cart)
    await db_session.flush()
    sku_id = uuid4()
    product_id = uuid4()
    cart_item = CartItem(cart_id=cart.id, sku_id=sku_id, product_id=product_id, quantity=1)
    db_session.add(cart_item)
    await db_session.commit()

    with patch("src.services.b2b_client.batch_get_products", side_effect=HTTPException(
        status_code=503, detail={"code": "B2B_UNAVAILABLE", "message": "B2B service is unavailable"}
    )):
        response = await client.get("/api/v1/cart")
        assert response.status_code == 503
        assert response.json()["code"] == "B2B_UNAVAILABLE"