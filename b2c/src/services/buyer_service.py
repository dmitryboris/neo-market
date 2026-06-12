from sqlalchemy.ext.asyncio import AsyncSession
from src.models.buyer import Buyer
from src.schemas.buyer import BuyerResponse, BuyerUpdateRequest


async def update_buyer(request: BuyerUpdateRequest,buyer: Buyer, session: AsyncSession) -> Buyer:
    if request.first_name is not None:
        buyer.first_name = request.first_name
    if request.last_name is not None:
        buyer.last_name = request.last_name
    if request.phone is not None:
        buyer.phone = request.phone
    await session.commit()
    await session.refresh(buyer)
    return buyer


async def delete_buyer(buyer: Buyer, session: AsyncSession) -> None:
    buyer.is_active = False
    await session.commit()
