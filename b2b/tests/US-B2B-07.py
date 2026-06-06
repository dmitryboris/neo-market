import pytest
from uuid import uuid4
from src.models import Product, ProductStatus, SKU, Category, ProductCharacteristic
from src.config import settings
from tests.conftest import TEST_SELLER_ID

@pytest.fixture
async def visible_product(db_session):
    cat = Category(id=uuid4(), name="Test Cat")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Visible",
        slug="visible",
        description="Test",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod)
    sku = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU1",
        price=10000,
        active_quantity=5,
        cost_price=5000,
        discount=0,
        stock_quantity=5,
        reserved_quantity=0,
        article="art",
    )
    db_session.add(sku)
    await db_session.commit()
    return prod

@pytest.fixture
async def invisible_product_out_of_stock(db_session):
    cat = Category(id=uuid4(), name="Test Cat2")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Out of stock",
        slug="out",
        description="No stock",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod)
    sku = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU2",
        price=20000,
        active_quantity=0,
        cost_price=5000,
        discount=0,
        stock_quantity=0,
        reserved_quantity=0,
        article="art",
    )
    db_session.add(sku)
    await db_session.commit()
    return prod

@pytest.fixture
async def invisible_product_hard_blocked(db_session):
    cat = Category(id=uuid4(), name="Test Cat3")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Hard blocked",
        slug="hard",
        description="Blocked",
        status=ProductStatus.HARD_BLOCKED,
        deleted=False,
    )
    db_session.add(prod)
    sku = SKU(
        id=uuid4(),
        product_id=prod.id,
        name="SKU3",
        price=30000,
        active_quantity=5,
        cost_price=5000,
        discount=0,
        stock_quantity=5,
        reserved_quantity=0,
        article="art",
    )
    db_session.add(sku)
    await db_session.commit()
    return prod

@pytest.mark.asyncio
async def test_catalog_returns_moderated_in_stock_products(client, visible_product):
    response = await client.get(
        "/api/v1/public/products",
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert str(visible_product.id) in ids

@pytest.mark.asyncio
async def test_catalog_excludes_hard_blocked(client, invisible_product_hard_blocked):
    response = await client.get(
        "/api/v1/public/products",
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY}
    )
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    assert str(invisible_product_hard_blocked.id) not in ids

@pytest.mark.asyncio
async def test_catalog_missing_service_key_returns_401(client):
    response = await client.get("/api/v1/public/products")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_catalog_response_has_no_cost_price(client, visible_product):
    response = await client.get(
        "/api/v1/public/products",
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY}
    )
    data = response.json()
    for item in data["items"]:
        pass
    batch_resp = await client.post(
        "/api/v1/public/products/batch",
        json={"product_ids": [str(visible_product.id)]},
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY}
    )
    assert batch_resp.status_code == 200
    product = batch_resp.json()[0]
    for sku in product["skus"]:
        assert "cost_price" not in sku
        assert "reserved_quantity" not in sku

@pytest.mark.asyncio
async def test_batch_ids_returns_visible_subset(client, visible_product, invisible_product_out_of_stock):
    ids = [str(visible_product.id), str(invisible_product_out_of_stock.id)]
    response = await client.post(
        "/api/v1/public/products/batch",
        json={"product_ids": ids},
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY}
    )
    assert response.status_code == 200
    returned_ids = [p["id"] for p in response.json()]
    assert str(visible_product.id) in returned_ids
    assert str(invisible_product_out_of_stock.id) not in returned_ids


@pytest.mark.asyncio
async def test_catalog_filters_by_characteristics(client, db_session):
    cat = Category(id=uuid4(), name="Cat")
    db_session.add(cat)

    prod_apple = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Apple Phone",
        slug="apple-phone",
        description="Nice phone",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod_apple)
    char_apple = ProductCharacteristic(
        product_id=prod_apple.id, name="brand", value="apple"
    )
    db_session.add(char_apple)

    prod_samsung = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=cat.id,
        title="Samsung Phone",
        slug="samsung-phone",
        description="Nice phone",
        status=ProductStatus.MODERATED,
        deleted=False,
    )
    db_session.add(prod_samsung)
    char_samsung = ProductCharacteristic(
        product_id=prod_samsung.id, name="brand", value="samsung"
    )
    db_session.add(char_samsung)

    for prod in (prod_apple, prod_samsung):
        sku = SKU(
            id=uuid4(),
            product_id=prod.id,
            name="Base",
            price=10000,
            active_quantity=5,
            cost_price=5000,
            discount=0,
            stock_quantity=5,
            reserved_quantity=0,
            article="art",
        )
        db_session.add(sku)

    await db_session.commit()

    response = await client.get(
        "/api/v1/public/products",
        params={"filters[brand]": "apple"},
        headers={"X-Service-Key": settings.B2C_TO_B2B_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    assert str(prod_apple.id) in ids
    assert str(prod_samsung.id) not in ids