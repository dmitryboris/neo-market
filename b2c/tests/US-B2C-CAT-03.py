import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import HTTPException

MOCK_PRODUCT_DETAIL = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "seller_id": "22222222-2222-2222-2222-222222222222",
        "category_id": "11111111-1111-1111-1111-111111111111",
        "title": "iPhone 15",
        "slug": "iphone-15",
        "description": "Latest iPhone",
        "status": "MODERATED",
        "images": [
            {"id": str(uuid4()), "url": "http://example.com/img1.jpg", "ordering": 0},
            {"id": str(uuid4()), "url": "http://example.com/img2.jpg", "ordering": 1}
        ],
        "characteristics": [
            {"name": "Бренд", "value": "Apple"}
        ],
        "skus": [
            {
                "id": str(uuid4()),
                "product_id": "...",
                "name": "128GB",
                "price": 99990,
                "discount": 0,
                "stock_quantity": 10,
                "active_quantity": 5,
                "article": "IP15-128",
                "images": [{"id": str(uuid4()), "url": "http://example.com/sku.jpg", "ordering": 0}],
                "characteristics": [
                    {"name": "Цвет", "value": "Чёрный"}
                ]
            },
            {
                "id": str(uuid4()),
                "product_id": "...",
                "name": "256GB",
                "price": 119990,
                "discount": 10000,
                "stock_quantity": 3,
                "active_quantity": 0,
                "article": "IP15-256",
                "images": [],
                "characteristics": []
            }
        ],
        "cover_image": "http://example.com/cover.jpg",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
    }
]


@pytest.mark.asyncio
async def test_product_card_returns_full_data_with_skus(client):
    """Happy path: карточка товара содержит все нужные поля, SKU с ценами и наличием."""
    with patch("src.services.catalog_service._request_b2b", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = MOCK_PRODUCT_DETAIL
        response = await client.get("/api/v1/catalog/products/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["name"] == "iPhone 15"
    assert data["description"] == "Latest iPhone"
    assert len(data["images"]) == 2
    assert len(data["characteristics"]) == 1
    assert len(data["skus"]) == 2

    sku1 = data["skus"][0]
    assert sku1["price"] == 99990
    assert sku1["discount"] == 0
    assert sku1["available_quantity"] == 5
    assert sku1["in_stock"] is True
    assert "cost_price" not in sku1
    assert "reserved_quantity" not in sku1

    sku2 = data["skus"][1]
    assert sku2["available_quantity"] == 0
    assert sku2["in_stock"] is False


@pytest.mark.asyncio
async def test_cost_price_absent_in_response(client):
    """Явная проверка отсутствия запрещённых полей cost_price и reserved_quantity."""
    with patch("src.services.catalog_service._request_b2b", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = MOCK_PRODUCT_DETAIL
        response = await client.get("/api/v1/catalog/products/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 200
    data = response.json()
    for sku in data["skus"]:
        assert "cost_price" not in sku
        assert "reserved_quantity" not in sku


@pytest.mark.asyncio
async def test_blocked_product_returns_404(client):
    """Заблокированный/удалённый товар возвращает 404."""
    with patch("src.services.catalog_service._request_b2b", side_effect=HTTPException(status_code=404)):
        response = await client.get("/api/v1/catalog/products/550e8400-e29b-41d4-a716-446655440000")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"