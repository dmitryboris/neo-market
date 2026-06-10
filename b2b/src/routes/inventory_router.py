from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import require_b2c_key
from src.schemas.inventory import ReserveRequest, ReserveResponse, InventoryOrderRequest, InventoryOrderResponse
from src.services.inventory_service import reserve_skus, unreserve_skus

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"], dependencies=[Depends(require_b2c_key)])

@inventory_router.post("/reserve", response_model=ReserveResponse)
async def reserve_endpoint(
    request: ReserveRequest,
    session: AsyncSession = Depends(get_session),
):
    items = [{"sku_id": i.sku_id, "quantity": i.quantity} for i in request.items]
    return await reserve_skus(session, request.idempotency_key, request.order_id, items)

@inventory_router.post("/unreserve", response_model=InventoryOrderResponse)
async def unreserve_endpoint(
    request: InventoryOrderRequest,
    session: AsyncSession = Depends(get_session),
):
    items = [{"sku_id": i.sku_id, "quantity": i.quantity} for i in request.items]
    return await unreserve_skus(session, request.order_id, items)