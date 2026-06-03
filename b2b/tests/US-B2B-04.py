import pytest
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import select
from httpx import AsyncClient
from src.models import Product, ProductStatus, Category, SKU
from tests.conftest import TEST_SELLER_ID


@pytest.fixture
async def product(db_session):
    """Продукт, принадлежащий TEST_SELLER, в статусе CREATED."""
    category_id = uuid4()
    cat = Category(id=category_id, name="Test Category")
    db_session.add(cat)

    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=category_id,
        title="Product to delete",
        slug=f"del-prod-{uuid4().hex[:8]}",
        description="Test",
        status=ProductStatus.CREATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.mark.asyncio
async def test_delete_sets_deleted_true(client, db_session, product):
    """После DELETE /products/{id} поле deleted становится True."""
    assert product.deleted is False

    response = await client.delete(f"/api/v1/products/{product.id}")
    assert response.status_code == 204

    await db_session.refresh(product)
    assert product.deleted is True


@pytest.mark.asyncio
async def test_delete_emits_event_to_moderation(client, db_session, product):
    """При удалении отправляется событие DELETED в Moderation."""
    with patch("src.services.product_service._send_moderation_event") as mock_mod:
        response = await client.delete(f"/api/v1/products/{product.id}")
        assert response.status_code == 204

        mock_mod.assert_called_once()
        args, _ = mock_mod.call_args
        sent_product = args[0]
        assert sent_product.id == product.id
        if len(args) > 1:
            assert args[1] == "DELETED"


@pytest.mark.asyncio
async def test_delete_emits_product_deleted_to_b2c(client, db_session, product):
    """При удалении отправляется событие PRODUCT_DELETED в B2C с sku_ids."""
    sku1 = SKU(
        id=uuid4(),
        product_id=product.id,
        name="SKU 1",
        price=1000,
        discount=0,
        stock_quantity=10,
        active_quantity=10,
        reserved_quantity=0,
        article="art1",
    )
    sku2 = SKU(
        id=uuid4(),
        product_id=product.id,
        name="SKU 2",
        price=2000,
        discount=0,
        stock_quantity=5,
        active_quantity=5,
        reserved_quantity=0,
        article="art2",
    )
    db_session.add_all([sku1, sku2])
    await db_session.commit()

    with patch("src.services.product_service._send_b2c_event") as mock_b2c:
        response = await client.delete(f"/api/v1/products/{product.id}")
        assert response.status_code == 204

        mock_b2c.assert_called_once()
        args, _ = mock_b2c.call_args
        sku_ids_arg = args[1] if len(args) > 1 else args[0].sku_ids
        if isinstance(sku_ids_arg, list):
            assert set(sku_ids_arg) == {sku1.id, sku2.id}


@pytest.mark.asyncio
async def test_delete_already_deleted_returns_400(client, db_session, product):
    """Повторное удаление возвращает 400."""
    response = await client.delete(f"/api/v1/products/{product.id}")
    assert response.status_code == 204

    response = await client.delete(f"/api/v1/products/{product.id}")
    assert response.status_code == 400
    data = response.json()
    assert "already deleted" in data["message"].lower() or "already deleted" in data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_deleted_product_not_in_seller_list(client, db_session, product):
    """Удалённый товар не отображается в списке продавца."""
    response = await client.delete(f"/api/v1/products/{product.id}")
    assert response.status_code == 204

    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    product_ids = [p["id"] for p in data["items"]]
    assert str(product.id) not in product_ids