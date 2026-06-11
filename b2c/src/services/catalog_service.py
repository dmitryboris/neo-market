import httpx
from uuid import uuid4
from src.config import settings
from src.schemas.catalog import (
    CatalogFilterSchema,
    CatalogProductCardSchema,
    CatalogPaginatedResponseSchema,
    CatalogProductDetailResponseSchema,
    CatalogProductDetailSkuSchema,
    CatalogProductDetailImageSchema,
    CatalogProductDetailCharacteristicSchema,
    ImageRefSchema,
    CatalogFacetsResponseSchema
)
from src.services.exceptions import ServiceUnavailable, InvalidSort, ProductNotFound
from src.services.communication_service import _request_b2b


async def get_products(
    filters: CatalogFilterSchema,
    search: str | None = None,
    sort: str = "created_desc",
    limit: int = 20,
    offset: int = 0,
) -> CatalogPaginatedResponseSchema:
    allowed_sorts = {"rating", "popularity", "price_asc", "price_desc", "date_desc", "discount_desc", "created_desc"}
    if sort not in allowed_sorts:
        raise InvalidSort(list(allowed_sorts))

    params = {
        "category_id": str(filters.category_id) if filters.category_id else None,
        "search": search,
        "min_price": filters.price_min,
        "max_price": filters.price_max,
        "seller_id": str(filters.seller_id) if filters.seller_id else None,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    params = {k: v for k, v in params.items() if v is not None}

    data = await _request_b2b("GET", "/api/v1/public/products", params=params)

    items = []
    for item in data["items"]:
        images = []
        if item.get("cover_image"):
            images.append({"id": str(uuid4()), "url": item["cover_image"], "alt": None, "ordering": 0, "is_main": None})
        image_objects = [ImageRefSchema(**img) for img in images]
        has_stock = item["min_price"] > 0
        items.append(CatalogProductCardSchema(
            id=item["id"],
            name=item["title"],
            slug=item["slug"],
            category=None,
            min_price=item["min_price"],
            old_price=None,
            has_stock=has_stock,
            rating=None,
            reviews_count=None,
            images=image_objects,
            seller=None,
        ))

    return CatalogPaginatedResponseSchema(
        items=items,
        total_count=data["total_count"],
        limit=data["limit"],
        offset=data["offset"],
    )

async def get_product_detail(product_id: str) -> CatalogProductDetailResponseSchema:
    data = await _request_b2b("POST", "/api/v1/public/products/batch", json={"product_ids": [product_id]})

    if not data:
        raise ProductNotFound()

    item = data[0]

    skus = []
    min_price = None
    has_stock = False
    for sku in item.get("skus", []):
        sku_image = sku["images"][0]["url"] if sku.get("images") else None
        sku_chars = [CatalogProductDetailCharacteristicSchema(name=c["name"], value=c["value"]) for c in sku.get("characteristics", [])]
        in_stock = sku["active_quantity"] > 0
        skus.append(CatalogProductDetailSkuSchema(
            id=sku["id"],
            name=sku["name"],
            price=sku["price"],
            discount=sku.get("discount", 0),
            image=sku_image,
            available_quantity=sku["active_quantity"],
            in_stock=in_stock,
            characteristics=sku_chars,
        ))
        if min_price is None or sku["price"] < min_price:
            min_price = sku["price"]
        if in_stock:
            has_stock = True

    images = [CatalogProductDetailImageSchema(id=img["id"], url=img["url"], ordering=img["ordering"]) for img in item.get("images", [])]
    characteristics = [CatalogProductDetailCharacteristicSchema(name=c["name"], value=c["value"]) for c in item.get("characteristics", [])]

    return CatalogProductDetailResponseSchema(
        id=item["id"],
        slug=item["slug"],
        name=item["title"],
        description=item.get("description", ""),
        status=item["status"],
        min_price=min_price or 0,
        has_stock=has_stock,
        images=images,
        characteristics=characteristics,
        skus=skus,
    )

async def get_facets(filters: CatalogFilterSchema) -> CatalogFacetsResponseSchema:
    """Проксирует запрос фасетов к B2B (???? какие фасеты такова нет)."""
    params = {}
    if filters.category_id:
        params["category_id"] = str(filters.category_id)
    data = await _request_b2b("GET", "/api/v1/catalog/facets", params=params)
    return CatalogFacetsResponseSchema(**data)