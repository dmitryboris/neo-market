from fastapi import APIRouter, Depends, Query, HTTPException, Header,Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from src.database import get_session
from src.schemas.product import (
    ProductPublicPaginatedResponse,
    ProductPublicShortResponse,
    ProductPublicResponse,
    BatchProductRequest,
)
from src.services.product_service import list_public_products, get_public_products_by_ids
from src.dependencies import require_b2c_key
import re

public_router = APIRouter(prefix="/public/products", tags=["Public Catalog"], dependencies=[Depends(require_b2c_key)])


@public_router.get("", response_model=ProductPublicPaginatedResponse)
async def list_public_products_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
    category_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None, min_length=3),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    seller_id: Optional[UUID] = Query(None),
    sort: str = Query("created_desc", pattern="^(price_asc|price_desc|created_desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    filters = {}
    for key, value in request.query_params.items():
        if key.startswith("filters["):
            match = re.match(r'filters\[([^\]]+)\]', key)
            if match:
                filter_name = match.group(1)
                filters.setdefault(filter_name, []).append(value)
    
    return await list_public_products(
        session=session,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        seller_id=seller_id,
        sort=sort,
        limit=limit,
        offset=offset,
        filters=filters,
    )

@public_router.post("/batch", response_model=list[ProductPublicResponse])
async def batch_public_products(
    request: BatchProductRequest,
    session: AsyncSession = Depends(get_session)
):
    products = await get_public_products_by_ids(session, request.product_ids)
    return products