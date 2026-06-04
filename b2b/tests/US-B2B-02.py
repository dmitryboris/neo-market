import pytest
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import select
from httpx import AsyncClient
from src.models import SKU, Product, ProductStatus, Seller, Category

from tests.conftest import TEST_SELLER_ID


@pytest.fixture
async def product(db_session):
    """Создаёт товар со статусом CREATED для тестов SKU."""
    category_id = uuid4()
    cat = Category(id=category_id, name="Test Category")
    db_session.add(cat)
    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=category_id,
        title="Test Product {uuid4()}",
        slug=f"test-product-{uuid4().hex[:8]}",
        description="Test description",
        # images=[{"url": "http://ex.com/i.jpg", "ordering": 0}],
        # characteristics=[{"name": "Brand", "value": "X"}],
        status=ProductStatus.CREATED
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest.mark.asyncio
async def test_first_sku_transitions_product_to_on_moderation(client, db_session, product):
    assert product.status == ProductStatus.CREATED

    sku_payload = {
        "product_id": str(product.id),
        "name": "First SKU",
        "price": 10000,
        "cost_price": 5000,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
        "characteristics": [{"name": "Color", "value": "Black"}]
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    print(response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "First SKU"

    await db_session.refresh(product)
    assert product.status == ProductStatus.ON_MODERATION

    stmt = select(SKU).where(SKU.product_id == product.id)
    result = await db_session.execute(stmt)
    skus = result.scalars().all()
    assert len(skus) == 1
    assert skus[0].name == "First SKU"


@pytest.mark.asyncio
async def test_second_sku_no_state_change(client, db_session, product):
    sku1_payload = {
        "product_id": str(product.id),
        "name": "First SKU",
        "price": 10000,
        "cost_price": 5000,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response1 = await client.post("/api/v1/skus", json=sku1_payload)
    print(response1.json())
    assert response1.status_code == 201
    await db_session.refresh(product)
    assert product.status == ProductStatus.ON_MODERATION

    sku2_payload = {
        "product_id": str(product.id),
        "name": "Second SKU",
        "price": 20000,
        "cost_price": 10000,
        "images": [{"url": "http://ex.com/img2.jpg", "ordering": 0}],
    }
    response2 = await client.post("/api/v1/skus", json=sku2_payload)
    assert response2.status_code == 201

    await db_session.refresh(product)
    assert product.status == ProductStatus.ON_MODERATION

    stmt = select(SKU).where(SKU.product_id == product.id)
    result = await db_session.execute(stmt)
    skus = result.scalars().all()
    assert len(skus) == 2


@pytest.mark.asyncio
async def test_first_sku_emits_created_event_to_moderation(client, db_session, product):
    with patch("src.services.sku_service._send_moderation_event") as mock_event:
        sku_payload = {
            "product_id": str(product.id),
            "name": "Event SKU",
            "price": 10000,
            "cost_price": 5000,
            "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
        }
        response = await client.post("/api/v1/skus", json=sku_payload)
        print(response.json())
        assert response.status_code == 201

        mock_event.assert_called_once()
        args, kwargs = mock_event.call_args
        product_arg = args[0]
        assert product_arg.id == product.id
        assert product_arg.status == ProductStatus.ON_MODERATION


@pytest.mark.asyncio
async def test_add_sku_to_hard_blocked_returns_403(client, db_session, product):
    product.status = ProductStatus.HARD_BLOCKED
    await db_session.commit()

    sku_payload = {
        "product_id": str(product.id),
        "name": "Blocked SKU",
        "price": 10000,
        "cost_price": 5000,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    print(response.json())
    assert response.status_code == 403
    assert "hard-blocked" in response.text.lower()

    stmt = select(SKU).where(SKU.product_id == product.id)
    result = await db_session.execute(stmt)
    skus = result.scalars().all()
    assert len(skus) == 0


@pytest.mark.asyncio
async def test_missing_image_returns_400(client, db_session, product):
    sku_payload = {
        "product_id": str(product.id),
        "name": "No Image SKU",
        "price": 10000,
        "cost_price": 5000,
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    assert response.status_code == 400
    assert "image" in response.text.lower()

# Доп тесты на кастом ошибки

@pytest.mark.asyncio
async def test_sku_product_not_found_returns_404(client):
    """Создание SKU для несуществующего product_id возвращает 404."""
    sku_payload = {
        "product_id": str(uuid4()),
        "name": "Test SKU",
        "price": 10000,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    if response.status_code != 201:
        print(f"ERROR {response.status_code}: {response.text}")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert data["message"] == "Product not found"


@pytest.mark.asyncio
async def test_sku_price_zero_or_negative_returns_400(client, product):
    """Цена <= 0 возвращает 400 с соответствующим сообщением."""
    sku_payload = {
        "product_id": str(product.id),
        "name": "Bad Price SKU",
        "price": 0,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "price must be a positive integer (kopecks)"


@pytest.mark.asyncio
async def test_sku_cost_price_zero_or_negative_returns_400(client, product):
    """cost_price <= 0 возвращает 400 с соответствующим сообщением."""
    sku_payload = {
        "product_id": str(product.id),
        "name": "Bad Cost SKU",
        "price": 1000,
        "cost_price": -1,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "cost_price must be a positive integer (kopecks)"


@pytest.mark.asyncio
async def test_sku_empty_name_returns_400(client, product):
    """Пустое или пробельное имя возвращает 400 с сообщением 'name is required'."""
    sku_payload = {
        "product_id": str(product.id),
        "name": "   ",
        "price": 1000,
        "images": [{"url": "http://ex.com/img.jpg", "ordering": 0}],
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "name is required"


@pytest.mark.asyncio
async def test_sku_missing_image_returns_400(client, product):
    """Отсутствие изображений возвращает 400 с сообщением 'image is required'.
    (Дополнительный тест с проверкой точного формата ошибки).
    """
    sku_payload = {
        "product_id": str(product.id),
        "name": "No Image SKU",
        "price": 1000,
        # images отсутствуют
    }
    response = await client.post("/api/v1/skus", json=sku_payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert data["message"] == "image is required"