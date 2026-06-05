from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.models import Seller
from src.schemas.sku import SKUCreate, SKUResponse, SKUUpdate, SKUImageResponse
from src.services import sku_service
from src.services.exceptions import ProductNotFound, ForbiddenOperation
from src.services.image_service import add_sku_image, update_sku_image, delete_sku_image
from src.schemas.image import ImageAttachRequest, ImageUpdateRequest

sku_router = APIRouter(prefix="/skus", tags=["SKU"])


@sku_router.post("", response_model=SKUResponse, status_code=status.HTTP_201_CREATED)
async def create_sku(
        request: SKUCreate,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    return await sku_service.create_sku(session, current_seller.id, request)


@sku_router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(
        sku_id: str,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    return await sku_service.get_sku_by_id(session, sku_id, current_seller.id)



@sku_router.patch("/{sku_id}", response_model=SKUResponse)
async def update_sku(
        sku_id: str,
        request: SKUUpdate,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    sku = await sku_service.get_sku_by_id(session, sku_id, current_seller.id)
    return await sku_service.update_sku(session, sku, request)


@sku_router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(
        sku_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    sku = await sku_service.get_sku_by_id(session, sku_id, current_seller.id)
    if not sku:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"code": "NOT_FOUND", "message": "SKU not found"})
    await sku_service.delete_sku(session, sku)


@sku_router.post("/{sku_id}/images", response_model=SKUImageResponse, status_code=status.HTTP_201_CREATED)
async def add_sku_image_endpoint(
        sku_id: UUID,
        request: ImageAttachRequest,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    try:
        image = await add_sku_image(session, sku_id, current_seller.id, request.url, request.ordering)
        return image
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SKU or image data")


@sku_router.patch("/images/{image_id}", response_model=SKUImageResponse)
async def update_sku_image_endpoint(
        image_id: UUID,
        request: ImageUpdateRequest,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    if request.url is None and request.ordering is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="At least one field (url or ordering) must be provided")
    try:
        image = await update_sku_image(session, image_id, current_seller.id, request.url, request.ordering)
        return image
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image data")


@sku_router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku_image_endpoint(
        image_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    try:
        await delete_sku_image(session, image_id, current_seller.id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete image")
