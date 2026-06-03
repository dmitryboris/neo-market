import pytest
from uuid import uuid4
from unittest.mock import patch
from httpx import AsyncClient
from src.models import (
    Product,
    ProductStatus,
    Category,
    SKU,
    Seller,
)
from tests.conftest import TEST_SELLER_ID


@pytest.fixture
async def moderated_product(db_session):
    """Продукт в статусе MODERATED, принадлежит TEST_SELLER."""
    cat = Category(id=uuid4(), name="Cat Mod")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Moderated Product",
        slug=f"mod-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def blocked_product(db_session):
    """Продукт в статусе BLOCKED, принадлежит TEST_SELLER."""
    cat = Category(id=uuid4(), name="Cat Blk")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Blocked Product",
        slug=f"blk-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.BLOCKED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def hard_blocked_product(db_session):
    """Продукт в статусе HARD_BLOCKED, принадлежит TEST_SELLER."""
    cat = Category(id=uuid4(), name="Cat Hard")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Hard Blocked Product",
        slug=f"hard-{uuid4().hex[:8]}",
        description="desc",
        status=ProductStatus.HARD_BLOCKED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def others_product(db_session):
    """Продукт, принадлежащий другому продавцу."""
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
    cat = Category(id=uuid4(), name="Cat Other")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=other.id,
        category_id=cat.id,
        title="Others Product",
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
async def test_edit_moderated_product_returns_to_on_moderation(
    client, db_session, moderated_product
):
    """Правка MODERATED товара переводит его в ON_MODERATION и отправляет событие EDITED."""
    assert moderated_product.status == ProductStatus.MODERATED

    patch_payload = {"title": "Updated Moderated Title"}

    with patch("src.services.moderation_service.send_event") as mock_event:
        response = await client.patch(
            f"/api/v1/products/{moderated_product.id}", json=patch_payload
        )
        assert response.status_code == 200

        await db_session.refresh(moderated_product)
        assert moderated_product.status == ProductStatus.ON_MODERATION

        mock_event.assert_called_once()
        args, _ = mock_event.call_args
        assert args[0] == "EDITED"
        assert args[1].id == moderated_product.id


@pytest.mark.asyncio
async def test_edit_blocked_product_returns_to_on_moderation(
    client, db_session, blocked_product
):
    """Правка BLOCKED товара переводит его в ON_MODERATION и отправляет событие EDITED."""
    assert blocked_product.status == ProductStatus.BLOCKED

    patch_payload = {"description": "Updated description"}

    with patch("src.services.moderation_service.send_event") as mock_event:
        response = await client.patch(
            f"/api/v1/products/{blocked_product.id}", json=patch_payload
        )
        assert response.status_code == 200

        await db_session.refresh(blocked_product)
        assert blocked_product.status == ProductStatus.ON_MODERATION

        mock_event.assert_called_once()
        args, _ = mock_event.call_args
        assert args[0] == "EDITED"
        assert args[1].id == blocked_product.id


@pytest.mark.asyncio
async def test_reserves_preserved_after_sku_edit(client, db_session):
    """reserved_quantity SKU не изменяется при редактировании SKU."""
    cat = Category(id=uuid4(), name="Cat SKU Edit")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Prod for SKU edit",
        slug=f"sku-edit-{uuid4().hex[:8]}",
        status=ProductStatus.CREATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.flush()

    sku = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="Original SKU",
        price=1000,
        discount=0,
        cost_price=500,
        stock_quantity=10,
        active_quantity=8,
        reserved_quantity=2,
        article="art-001",
    )
    db_session.add(sku)
    await db_session.commit()
    await db_session.refresh(sku)

    reserved_before = sku.reserved_quantity
    update_payload = {"name": "Updated SKU", "price": 1200}
    response = await client.put(f"/api/v1/skus/{sku.id}", json=update_payload)
    assert response.status_code == 200

    await db_session.refresh(sku)
    assert sku.reserved_quantity == reserved_before


@pytest.mark.asyncio
async def test_edit_hard_blocked_returns_403(client, hard_blocked_product):
    """Любая правка HARD_BLOCKED товара возвращает 403."""
    patch_payload = {"title": "Hacked title"}
    response = await client.patch(
        f"/api/v1/products/{hard_blocked_product.id}", json=patch_payload
    )
    assert response.status_code == 403
    data = response.json()
    assert "hard-blocked" in data["message"].lower() or "hard_blocked" in data["message"].lower()


@pytest.mark.asyncio
async def test_edit_others_product_returns_403(client, others_product):
    """Правка чужого товара возвращает 403."""
    patch_payload = {"title": "Stolen"}
    response = await client.patch(
        f"/api/v1/products/{others_product.id}", json=patch_payload
    )
    assert response.status_code == 403
    data = response.json()
    assert "access denied" in data["message"].lower() or "forbidden" in data["message"].lower()