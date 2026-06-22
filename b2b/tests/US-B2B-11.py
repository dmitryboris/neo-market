import pytest
from uuid import uuid4
from httpx import AsyncClient
from src.models import Product, ProductStatus, Category, Seller
from tests.conftest import TEST_SELLER_ID


async def _create_category(db_session, name="Test Category"):
    cat = Category(id=uuid4(), name=name)
    db_session.add(cat)
    await db_session.flush()
    return cat


async def _create_product(db_session, seller_id, category_id, title, status=ProductStatus.CREATED, deleted=False):
    prod = Product(
        id=uuid4(),
        seller_id=seller_id,
        category_id=category_id,
        title=title,
        slug=title.lower().replace(" ", "-")[:255] + f"-{uuid4().hex[:6]}",
        description="desc",
        status=status,
        deleted=deleted,
    )
    db_session.add(prod)
    await db_session.flush()
    return prod


@pytest.mark.asyncio
async def test_list_returns_only_own_products(client: AsyncClient, db_session):
    """Продавец видит только свои товары."""
    cat = await _create_category(db_session)
    my_prod = await _create_product(db_session, TEST_SELLER_ID, cat.id, "My Product")
    other_seller = Seller(
        id=uuid4(),
        email="other@example.com",
        first_name="Other",
        last_name="Seller",
        company_name="OtherCo",
        inn="1234567890",
        password_hash="hash",
        role="seller",
        is_active=True,
    )
    db_session.add(other_seller)
    await db_session.flush()
    other_prod = await _create_product(db_session, other_seller.id, cat.id, "Other Product")

    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    product_ids = [item["id"] for item in data["items"]]
    assert str(my_prod.id) in product_ids
    assert str(other_prod.id) not in product_ids


@pytest.mark.asyncio
async def test_idor_query_param_seller_id_ignored(client: AsyncClient, db_session):
    """Параметр seller_id в query игнорируется — чужие товары не отдаются."""
    cat = await _create_category(db_session)
    my_prod = await _create_product(db_session, TEST_SELLER_ID, cat.id, "My Product")
    other_seller = Seller(
        id=uuid4(),
        email="other2@example.com",
        first_name="Other2",
        last_name="Seller2",
        company_name="OtherCo2",
        inn="1234567892",
        password_hash="hash",
        role="seller",
        is_active=True,
    )
    db_session.add(other_seller)
    await db_session.flush()
    other_prod = await _create_product(db_session, other_seller.id, cat.id, "Other Product 2")

    response = await client.get(f"/api/v1/products?seller_id={other_seller.id}")
    assert response.status_code == 200
    data = response.json()
    product_ids = [item["id"] for item in data["items"]]
    assert str(my_prod.id) in product_ids
    assert str(other_prod.id) not in product_ids


@pytest.mark.asyncio
async def test_deleted_products_visible_with_deleted_flag(client: AsyncClient, db_session):
    """С include_deleted=true видно удалённые товары, по умолчанию — нет."""
    cat = await _create_category(db_session)
    active = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Active")
    deleted = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Deleted", deleted=True)

    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert str(active.id) in ids
    assert str(deleted.id) not in ids

    resp = await client.get("/api/v1/products?include_deleted=true")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert str(active.id) in ids
    assert str(deleted.id) in ids


@pytest.mark.asyncio
async def test_status_filter_works_correctly(client: AsyncClient, db_session):
    """Фильтр по статусу отбирает только нужные товары."""
    cat = await _create_category(db_session)
    p1 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Product 1", status=ProductStatus.CREATED)
    p2 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Product 2", status=ProductStatus.BLOCKED)
    p3 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Product 3", status=ProductStatus.BLOCKED)

    resp = await client.get("/api/v1/products?status=BLOCKED")
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert str(p1.id) not in ids
    assert str(p2.id) in ids
    assert str(p3.id) in ids


@pytest.mark.asyncio
async def test_search_by_title_case_insensitive(client: AsyncClient, db_session):
    """Поиск нечувствителен к регистру и работает по подстроке."""
    cat = await _create_category(db_session)
    p1 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "iPhone 15 Pro")
    p2 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Samsung Galaxy S24")
    p3 = await _create_product(db_session, TEST_SELLER_ID, cat.id, "Apple iPad")

    resp = await client.get("/api/v1/products?search=iphone")
    assert resp.status_code == 200

    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert str(p1.id) in ids
    assert str(p2.id) not in ids
    assert str(p3.id) not in ids

    resp = await client.get("/api/v1/products?search=SAMSUNG")
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert str(p2.id) in ids
