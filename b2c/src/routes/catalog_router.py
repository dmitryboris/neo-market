from fastapi import APIRouter, Query, HTTPException
from uuid import UUID
from src.services import catalog_service
from src.schemas.catalog import (
    CatalogFilterSchema,
    CatalogPaginatedResponseSchema,
    CatalogProductDetailResponseSchema,
    CatalogFacetsResponseSchema
)

catalog_router = APIRouter(prefix="/catalog", tags=["Catalog"])


@catalog_router.get("/products", response_model=CatalogPaginatedResponseSchema)
async def catalog_products(
        filter_category_id: UUID | None = Query(None, alias="filter[category_id]"),
        filter_price_min: int | None = Query(None, alias="filter[price_min]"),
        filter_price_max: int | None = Query(None, alias="filter[price_max]"),
        filter_seller_id: UUID | None = Query(None, alias="filter[seller_id]"),
        q: str | None = None,
        sort: str = "created_desc",
        limit: int = 20,
        offset: int = 0,
):
    filters = CatalogFilterSchema(
        category_id=filter_category_id,
        price_min=filter_price_min,
        price_max=filter_price_max,
        seller_id=filter_seller_id,
    )
    return await catalog_service.get_products(filters=filters, search=q, sort=sort, limit=limit, offset=offset)


@catalog_router.get("/products/{product_id}", response_model=CatalogProductDetailResponseSchema)
async def product_detail(product_id: str):
    return await catalog_service.get_product_detail(product_id)


@catalog_router.get("/facets", response_model=CatalogFacetsResponseSchema)
async def facets(
        filter_category_id: UUID | None = Query(None, alias="filter[category_id]"),
        # другие фильтры
):
    filters = CatalogFilterSchema(category_id=filter_category_id)
    return await catalog_service.get_facets(filters)


# Остальные эндпоинты не реализованы
@catalog_router.get("/categories")
async def categories():
    raise HTTPException(status_code=501)


@catalog_router.get("/categories/tree")
async def categories_tree():
    raise HTTPException(status_code=501)


@catalog_router.get("/banners")
async def banners():
    raise HTTPException(status_code=501)


@catalog_router.get("/collections")
async def collections():
    raise HTTPException(status_code=501)
