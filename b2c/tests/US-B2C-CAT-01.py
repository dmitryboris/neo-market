import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from src.main import app
from src.schemas.catalog import CatalogFacetsResponseSchema
from src.services.exceptions import CatalogUnavailable



@pytest.fixture
def mock_b2b_success_products():
    """Данные, имитирующие ответ B2B GET /api/v1/public/products."""
    return {
        "items": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "iPhone 15",
                "slug": "iphone-15",
                "category_id": "11111111-1111-1111-1111-111111111111",
                "min_price": 99990,
                "cover_image": "http://example.com/img.jpg",
                "status": "MODERATED",
                "created_at": "2026-01-01T00:00:00Z"
            }
        ],
        "total_count": 1,
        "limit": 20,
        "offset": 0
    }


@pytest.fixture
def mock_b2b_success_facets():
    """Данные, имитирующие ответ B2B GET /api/v1/catalog/facets."""
    return {
        "category_id": "11111111-1111-1111-1111-111111111111",
        "facets": [
            {
                "name": "brand",
                "values": [
                    {"value": "Apple", "count": 124},
                    {"value": "Samsung", "count": 98},
                ]
            },
            {
                "name": "color",
                "values": [
                    {"value": "черный", "count": 60},
                    {"value": "белый", "count": 40}
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_catalog_returns_filtered_sorted_products(client, mock_b2b_success_products):
    """Happy path: фильтр по категории и сортировка price_asc."""
    with patch("src.services.catalog_service._request_b2b", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_b2b_success_products

        response = await client.get(
            "/api/v1/catalog/products",
            params={
                "sort": "price_asc",
                "filter[category_id]": "11111111-1111-1111-1111-111111111111",
                "limit": 20,
                "offset": 0,
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["name"] == "iPhone 15"
    assert item["slug"] == "iphone-15"
    assert item["min_price"] == 99990
    assert item["has_stock"] is True
    assert item["category"] is None
    assert item["seller"] is None
    assert len(item["images"]) == 1
    assert item["images"][0]["url"] == "http://example.com/img.jpg"


@pytest.mark.asyncio
async def test_facets_return_counts_per_filter_value(client, mock_b2b_success_facets):
    """Фасеты возвращают корректные подсчёты."""
    with patch("src.services.catalog_service._request_b2b", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_b2b_success_facets

        response = await client.get(
            "/api/v1/catalog/facets",
            params={"filter[category_id]": "11111111-1111-1111-1111-111111111111"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "11111111-1111-1111-1111-111111111111"
    assert len(data["facets"]) == 2

    brand_facet = data["facets"][0]
    assert brand_facet["name"] == "brand"
    assert len(brand_facet["values"]) == 2
    assert brand_facet["values"][0]["value"] == "Apple"
    assert brand_facet["values"][0]["count"] == 124

    color_facet = data["facets"][1]
    assert color_facet["name"] == "color"


@pytest.mark.asyncio
async def test_invalid_sort_returns_400(client):
    """Невалидный sort возвращает 400 с перечислением допустимых."""
    with patch("src.services.catalog_service._request_b2b", new_callable=AsyncMock) as mock_req:
        response = await client.get("/api/v1/catalog/products", params={"sort": "illegal"})

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert "Invalid sort parameter" in data["message"]
    mock_req.assert_not_called()


@pytest.mark.asyncio
async def test_b2b_unavailable_returns_502(client):
    """При недоступности B2B возвращается 503 Service Unavailable."""
    with patch("src.services.catalog_service._request_b2b", side_effect=CatalogUnavailable()):
        response = await client.get("/api/v1/catalog/products")

    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "SERVICE_UNAVAILABLE"
    assert data["message"] == "B2B service unavailable"