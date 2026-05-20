import pytest
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import get_session, Base, settings
from src.dependencies import get_current_user
from src.models import Seller, ProductStatus, Category, Product

from tests.conftest import TEST_SELLER_ID, _create_category


@pytest.mark.asyncio
async def test_create_product_201(client, db_session, valid_payload):
    category_id = uuid4()
    await _create_category(db_session, category_id)
    valid_payload["category_id"] = str(category_id)

    response = await client.post("/api/v1/products", json=valid_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "CREATED"

    product_id = data["id"]
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    product = result.scalar_one()
    assert product.status == ProductStatus.CREATED
    assert product.seller_id == TEST_SELLER_ID
    assert product.category_id == category_id
    assert product.title == valid_payload["title"]


@pytest.mark.asyncio
async def test_seller_id_from_jwt(client, db_session, valid_payload):
    category_id = uuid4()
    await _create_category(db_session, category_id)
    valid_payload["category_id"] = str(category_id)

    response = await client.post("/api/v1/products", json=valid_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["seller_id"] == str(TEST_SELLER_ID)

    product_id = data["id"]
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    product = result.scalar_one()
    assert product.seller_id == TEST_SELLER_ID


@pytest.mark.asyncio
async def test_invalid_category_id_400(client, db_session, valid_payload):
    response = await client.post("/api/v1/products", json=valid_payload)
    assert response.status_code == 400
    assert "category not found" in response.text.lower()

    stmt = select(Product).where(Product.title == valid_payload["title"])
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_missing_images_400(client, valid_payload):
    payload = valid_payload.copy()
    payload.pop("images")
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    assert "image" in response.text.lower()


@pytest.mark.asyncio
async def test_missing_category_400(client, valid_payload):
    payload = valid_payload.copy()
    payload.pop("category_id")
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 400
    assert "category" in response.text.lower()
