import pytest
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient
from src.models import (
    Product,
    ProductStatus,
    Category,
    SKU,
    Seller,
    BlockingReason,
    FieldReport,
)
from tests.conftest import TEST_SELLER_ID



@pytest.fixture
async def moderated_product(db_session):
    """Товар в статусе MODERATED с одним SKU (у которого есть cost_price)."""
    cat = Category(id=uuid4(), name="Category for MODERATED")
    db_session.add(cat)

    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Moderated Product",
        slug=f"mod-prod-{uuid4().hex[:8]}",
        description="A moderated product",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.flush()

    sku = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU for moderated",
        price=15000,
        discount=0,
        cost_price=7000,
        stock_quantity=10,
        active_quantity=10,
        reserved_quantity=2,
        article="mod-art",
    )
    db_session.add(sku)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def blocked_product_with_details(db_session):
    """Товар в статусе BLOCKED с причиной блокировки и field_reports."""
    cat = Category(id=uuid4(), name="Category for BLOCKED")
    db_session.add(cat)

    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Blocked Product",
        slug=f"blk-prod-{uuid4().hex[:8]}",
        description="A blocked product",
        status=ProductStatus.BLOCKED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.flush()

    reason = BlockingReason(
        id=uuid4(),
        title="Violation of rules",
        comment="Bad content",
    )
    db_session.add(reason)

    report1 = FieldReport(
        id=uuid4(),
        product_id=prod.id,
        field_name="title",
        comment="Title is misleading",
    )
    report2 = FieldReport(
        id=uuid4(),
        product_id=prod.id,
        field_name="description",
        comment="Description contains prohibited language",
    )
    db_session.add_all([report1, report2])
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.fixture
async def other_seller_product(db_session):
    """Товар, принадлежащий другому продавцу (не TEST_SELLER)."""
    other_seller = Seller(
        id=uuid4(),
        email=f"other_{uuid4()}@test.com",
        first_name="Other",
        last_name="Seller",
        company_name="Other Co",
        inn="1234567890",
        password_hash="fake",
    )
    db_session.add(other_seller)

    cat = Category(id=uuid4(), name="Other's Category")
    db_session.add(cat)

    prod = Product(
        id=uuid4(),
        seller_id=other_seller.id,
        category_id=cat.id,
        title="Other's Product",
        slug=f"other-{uuid4().hex[:8]}",
        description="Not mine",
        status=ProductStatus.CREATED,
        deleted=False,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod



@pytest.mark.asyncio
async def test_get_moderated_product_returns_full_payload(client, moderated_product):
    response = await client.get(f"/api/v1/products/{moderated_product.id}")
    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(moderated_product.id)
    assert data["status"] == "MODERATED"
    assert data["title"] == "Moderated Product"

    assert len(data["skus"]) == 1
    sku = data["skus"][0]
    assert sku["cost_price"] == 7000
    assert sku["reserved_quantity"] == 2

    assert data["blocking_reason"] is None
    assert isinstance(data.get("field_reports"), list)


@pytest.mark.asyncio
async def test_get_blocked_product_returns_blocking_reason_and_field_reports(
    client, blocked_product_with_details
):
    response = await client.get(f"/api/v1/products/{blocked_product_with_details.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "BLOCKED"

    reason = data["blocking_reason"]
    assert reason is not None
    assert reason["title"] == "Violation of rules"

    reports = data["field_reports"]
    assert len(reports) == 2
    fields = [r["field_name"] for r in reports]
    assert "title" in fields
    assert "description" in fields


@pytest.mark.asyncio
async def test_get_others_product_returns_404(client, other_seller_product):
    response = await client.get(f"/api/v1/products/{other_seller_product.id}")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client):
    fake_id = uuid4()
    response = await client.get(f"/api/v1/products/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"