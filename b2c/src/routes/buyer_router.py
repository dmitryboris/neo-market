from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.dependencies import get_current_user
from src.database import get_session
from src.models.buyer import Buyer
from src.schemas.buyer import BuyerResponse, BuyerUpdateRequest
from src.services import buyer_service

buyer_router = APIRouter(prefix="/buyers", tags=["Buyer"])


@buyer_router.get("/me", response_model=BuyerResponse)
async def get_me(current_buyer: Buyer = Depends(get_current_user)):
    return current_buyer


@buyer_router.patch("/me", response_model=BuyerResponse)
async def update_me(
        request: BuyerUpdateRequest,
        session: AsyncSession = Depends(get_session),
        current_buyer: Buyer = Depends(get_current_user),
):
    return await buyer_service.update_buyer(request, current_buyer, session)


@buyer_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
        session: AsyncSession = Depends(get_session),
        current_buyer: Buyer = Depends(get_current_user),
):
    await buyer_service.delete_buyer(current_buyer, session)
    return None
