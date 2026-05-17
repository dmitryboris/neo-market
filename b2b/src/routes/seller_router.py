from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.models.seller import Seller
from src.schemas.seller import SellerUpdate, SellerResponse
from src.services import seller_service

seller_router = APIRouter(prefix="/seller", tags=["Seller"])


@seller_router.get("/profile", response_model=SellerResponse, summary="My profile")
async def get_my_data(current_seller: Seller = Depends(get_current_user)):
    return current_seller


@seller_router.patch("/profile/update", response_model=SellerResponse, summary="Update profile")
async def update_me(
        request: SellerUpdate,
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    return await seller_service.update_seller(session, current_seller, request)


@seller_router.delete("/profile/delete", status_code=status.HTTP_204_NO_CONTENT, summary="Delete account")
async def delete_me(
        session: AsyncSession = Depends(get_session),
        current_seller: Seller = Depends(get_current_user),
):
    await seller_service.delete_seller(session, current_seller)
