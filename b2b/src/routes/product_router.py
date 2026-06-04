from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.models import Seller
from src.schemas.product import (
    ProductCreate, ProductResponse, ProductUpdate,
    ProductPaginatedResponse, ProductImageCreate,
    ProductImageResponse, ProductStatus
)
from src.schemas.image import ImageUpdateRequest
from src.services import product_service, sku_service
from src.services.exceptions import (
    CategoryNotFound, ProductNotFound, AccessDenied,
    ProductTitleEmpty, CategoryInvalid, ProductTitleInvalid, ProductImageNotFound
)
from src.services.image_service import add_product_image, update_product_image, delete_product_image
from src.schemas.sku import SKUResponse

product_router = APIRouter(prefix="/products", tags=["Products"])


@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(
        request: ProductCreate,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    product = await product_service.create_product(session, current_seller.id, request, request.category_id)
    return product


@product_router.get("", response_model=ProductPaginatedResponse)
async def get_my_products(
        limit: int = 20,
        offset: int = 0,
        status: ProductStatus | None = None,
        include_deleted: bool = False,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    data = await product_service.get_my_products(session, current_seller.id, limit, offset, status, include_deleted)
    return data


@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        product = await product_service.get_product_by_id(session, product_id, seller_id=current_seller.id)
        return product
    except (ProductNotFound, AccessDenied) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@product_router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
        product_id: UUID,
        request: ProductUpdate,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        product = await product_service.get_product_by_id(session, product_id, seller_id=current_seller.id)
        updated = await product_service.update_product(session, product, request)
        return updated
    except (ProductNotFound, AccessDenied) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CategoryNotFound as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@product_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
        product_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        product = await product_service.get_product_by_id(session, product_id, seller_id=current_seller.id)
        await product_service.delete_product(session, product)
    except (ProductNotFound, AccessDenied) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@product_router.post("/{product_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def add_product_image_endpoint(
        product_id: UUID,
        request: ProductImageCreate,  # ImageAttachRequest
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        image = await add_product_image(session, product_id, current_seller.id, request.url, request.ordering)
        return image
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@product_router.patch("/images/{image_id}", response_model=ProductImageResponse)
async def update_product_image_endpoint(
        image_id: UUID,
        request: ImageUpdateRequest,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        if request.url is None and request.ordering is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="At least one field (url or ordering) must be provided")
        image = await update_product_image(session, image_id, current_seller.id, request.url, request.ordering)
        return image
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@product_router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image_endpoint(
        image_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user)
):
    try:
        await delete_product_image(session, image_id, current_seller.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@product_router.get("/{product_id}/skus", response_model=list[SKUResponse])
async def get_product_skus(
        product_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    skus = await sku_service.get_skus_by_product(session, product_id, current_seller.id)
    return skus
