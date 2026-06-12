from uuid import UUID
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.order import OrderCreateRequest, OrderResponse
from src.services.order_service import create_order
from src.database import get_session
from src.dependencies import get_current_user
from src.models.buyer import Buyer

orders_router = APIRouter(prefix="/orders", tags=["Orders"])

@orders_router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    request: OrderCreateRequest,
    idempotency_key: UUID = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    current_user: Buyer = Depends(get_current_user),
):
    order = await create_order(
        session=session,
        buyer_id=current_user.id,
        idempotency_key=idempotency_key,
        address_id=request.address_id,
        payment_method_id=request.payment_method_id,
        comment=request.comment,
        items_snapshot=[i.model_dump() for i in request.items_snapshot] if request.items_snapshot else None,
    )
    return order