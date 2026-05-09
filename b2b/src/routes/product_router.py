from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.models import Seller
from src.schemas.product import (
    ProductCreateRequest, ProductResponse, ProductUpdateRequest,
    ProductMyListResponse, ProductImageUpdateRequest, ProductImageCreateRequest,
    ProductImageResponse
)
from src.services import product_service
from src.services.exceptions import CategoryNotFound, ProductNotFound, AccessDenied
from src.services.image_service import add_product_image, update_product_image, delete_product_image

product_router = APIRouter(prefix="/api/products", tags=["Products"])

def invalid_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "INVALID_REQUEST", "message": message})

def is_valid_uuid(val: str) -> bool:
    try:
        UUID(val)
        return True
    except (ValueError, AttributeError, TypeError):
        return False

@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(
    request: ProductCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    if not request.title or not request.title.strip():
        raise invalid_request("title is required")
    if len(request.title) > 255:
        raise invalid_request("title must be 1-255 characters")

    if not request.images:
        raise invalid_request("At least one image is required")
    
    if request.category_id is None:
        raise invalid_request("category_id is required")
    
    if not is_valid_uuid(request.category_id):
        raise invalid_request("category_id must be a valid UUID")

    category_uuid = UUID(request.category_id)

    try:
        product = await product_service.create_product(session, current_seller.id, request, category_uuid)
        return product
    except CategoryNotFound:
        raise invalid_request("Category not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@product_router.get("/my", response_model=ProductMyListResponse)
async def get_my_products(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    data = await product_service.get_my_products(session, current_seller.id, limit, offset)
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
    request: ProductUpdateRequest,
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
    request: ProductImageCreateRequest,
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
    request: ProductImageUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    try:
        if request.url is None and request.ordering is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field (url or ordering) must be provided")
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