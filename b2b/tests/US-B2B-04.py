import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from src.models import Product, ProductStatus, Category, SKU, Seller
from tests.conftest import TEST_SELLER_ID


@pytest.fixture
async def product(db_session):
    """Продукт со SKU, принадлежит TEST_SELLER, не удалён."""
    cat = Category(id=uuid4(), name="Del Cat")
    db_session.add(cat)

    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Product to delete",
        slug=f"del-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.CREATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.flush()

    sku1 = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU 1",
        price=1000,
        discount=0,
        cost_price=500,
        stock_quantity=10,
        active_quantity=10,
        reserved_quantity=0,
        article="art1",
    )
    sku2 = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU 2",
        price=2000,
        discount=0,
        cost_price=1000,
        stock_quantity=5,
        active_quantity=5,
        reserved_quantity=0,
        article="art2",
    )
    db_session.add_all([sku1, sku2])
    await db_session.commit()
    stmt = select(Product).where(Product.id == prod.id).options(selectinload(Product.skus))
    result = await db_session.execute(stmt)
    return result.scalar_one()


@pytest.fixture
async def deleted_product(db_session):
    """Уже мягко удалённый товар."""
    cat = Category(id=uuid4(), name="Already Deleted")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Already Deleted",
        slug=f"del-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.CREATED,
        deleted=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def others_product(db_session):
    """Товар другого продавца."""
    other = Seller(
        id=uuid4(),
        email=f"other_{uuid4()}@test.com",
        first_name="Other",
        last_name="Seller",
        company_name="Other Co",
        inn="1234567890",
        password_hash="fake",
    )
    db_session.add(other)
    cat = Category(id=uuid4(), name="Other Cat")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=other.id,
        category_id=cat.id,
        title="Other's Product",
        slug=f"other-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.CREATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.mark.asyncio
async def test_delete_sets_deleted_true(client, db_session, product):
    """Успешное удаление: deleted=True, статус 200, 'ok': true."""
    assert not product.deleted

    with patch("src.services.product_service._send_moderation_event", AsyncMock()), \
            patch("src.services.product_service._send_b2c_event", AsyncMock()):
        response = await client.delete(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    await db_session.refresh(product)
    assert product.deleted is True


@pytest.mark.asyncio
async def test_delete_emits_event_to_moderation(client, db_session, product):
    """При удалении отправляется DELETED в Moderation."""
    with patch("src.services.product_service._send_moderation_event") as mock_mod, \
            patch("src.services.product_service._send_b2c_event", AsyncMock()):
        response = await client.delete(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    mock_mod.assert_called_once_with(product, "DELETED")


@pytest.mark.asyncio
async def test_delete_emits_product_deleted_to_b2c(client, db_session, product):
    """При удалении отправляется PRODUCT_DELETED в B2C со списком sku_ids."""
    expected_sku_ids = {sku.id for sku in product.skus}

    with patch("src.services.product_service._send_b2c_event") as mock_b2c, \
            patch("src.services.product_service._send_moderation_event", AsyncMock()):
        response = await client.delete(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    mock_b2c.assert_called_once()
    args, _ = mock_b2c.call_args
    assert args[0] == product
    assert set(args[1]) == expected_sku_ids


@pytest.mark.asyncio
async def test_delete_already_deleted_returns_400(client, db_session, deleted_product):
    """Повторное удаление возвращает 400."""
    with patch("src.services.product_service._send_moderation_event", AsyncMock()), \
            patch("src.services.product_service._send_b2c_event", AsyncMock()):
        response = await client.delete(f"/api/v1/products/{deleted_product.id}")

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "Product already deleted"


@pytest.mark.asyncio
async def test_deleted_product_not_in_seller_list(client, db_session, product):
    """Удалённый товар не виден в стандартном списке продавца."""

    with patch("src.services.product_service._send_moderation_event", AsyncMock()), \
            patch("src.services.product_service._send_b2c_event", AsyncMock()):
        await client.delete(f"/api/v1/products/{product.id}")

    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    product_ids = [item["id"] for item in data["items"]]
    assert str(product.id) not in product_ids


@pytest.mark.asyncio
async def test_delete_others_product_returns_403(client, db_session, others_product):
    """Удаление чужого товара запрещено."""
    response = await client.delete(f"/api/v1/products/{others_product.id}")
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "NOT_OWNER"
    assert data["message"] == "Product does not belong to the authenticated seller"
