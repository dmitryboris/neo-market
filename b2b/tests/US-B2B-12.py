import pytest
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from src.models import SKU, Product, ProductStatus, Category
from tests.conftest import TEST_SELLER_ID


async def _create_sku(db_session, product_id, price=1000, reserved=0, active=10):
    sku = SKU(
        id=uuid4(),
        product_id=product_id,
        name="Test SKU",
        price=price,
        discount=0,
        cost_price=500,
        stock_quantity=10,
        active_quantity=active,
        reserved_quantity=reserved,
        article="art",
    )
    db_session.add(sku)
    await db_session.flush()
    return sku


async def _create_product(db_session, status=ProductStatus.MODERATED):
    cat = Category(id=uuid4(), name="Test")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Test",
        slug=f"prod-{uuid4().hex[:6]}",
        status=status,
    )
    db_session.add(prod)
    await db_session.flush()
    return prod


@pytest.mark.asyncio
async def test_delete_sku_succeeds(client, db_session):
    prod = await _create_product(db_session, ProductStatus.MODERATED)
    sku = await _create_sku(db_session, prod.id)
    response = await client.delete(f"/api/v1/skus/{sku.id}")
    assert response.status_code == 204
    result = await db_session.execute(select(SKU).where(SKU.id == sku.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_sku_with_active_reserves_returns_409(client, db_session):
    prod = await _create_product(db_session, ProductStatus.CREATED)
    sku = await _create_sku(db_session, prod.id, reserved=5)
    response = await client.delete(f"/api/v1/skus/{sku.id}")
    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_last_sku_on_moderation_transitions_product_to_created(client, db_session):
    prod = await _create_product(db_session, ProductStatus.ON_MODERATION)
    sku = await _create_sku(db_session, prod.id)
    with patch("src.services.sku_service._send_moderation_event", AsyncMock()) as mock_mod:
        response = await client.delete(f"/api/v1/skus/{sku.id}")
        assert response.status_code == 204
        await db_session.refresh(prod)
        assert prod.status == ProductStatus.CREATED
        mock_mod.assert_called_once()


@pytest.mark.asyncio
async def test_delete_sku_hard_blocked_product_returns_403(client, db_session):
    prod = await _create_product(db_session, ProductStatus.HARD_BLOCKED)
    sku = await _create_sku(db_session, prod.id)
    response = await client.delete(f"/api/v1/skus/{sku.id}")
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_sku_out_of_stock_event_on_moderated_product(client, db_session):
    prod = await _create_product(db_session, ProductStatus.MODERATED)
    sku = await _create_sku(db_session, prod.id, active=5)
    with patch("src.services.sku_service.send_sku_out_of_stock_event", AsyncMock()) as mock_b2c:
        response = await client.delete(f"/api/v1/skus/{sku.id}")
        assert response.status_code == 204
        mock_b2c.assert_called_once()
        args, _ = mock_b2c.call_args
        assert args[0] == sku
