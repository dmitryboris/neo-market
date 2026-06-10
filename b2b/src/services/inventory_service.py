from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import SKU, ReserveOperation, UnreserveOperation, Product
from src.services.exceptions import SKUNotFound, InsufficientStock, DomainException
from src.schemas.inventory import ReserveResponse, InventoryOrderResponse
from src.services.communication_service import send_sku_out_of_stock_event 

async def reserve_skus(
    session: AsyncSession,
    idempotency_key: UUID,
    order_id: UUID,
    items: list[dict],
) -> ReserveResponse:
    existing = await session.get(ReserveOperation, idempotency_key)
    if existing:
        return ReserveResponse.model_validate(existing.result)

    sku_ids = sorted([item["sku_id"] for item in items])
    stmt = select(SKU).where(SKU.id.in_(sku_ids)).with_for_update()
    result = await session.execute(stmt)
    skus = {sku.id: sku for sku in result.scalars().all()}
    if len(skus) != len(sku_ids):
        missing = set(sku_ids) - set(skus.keys())
        raise SKUNotFound(f"SKU(s) {missing} not found")

    failed = []
    updates = []
    for item in items:
        sku = skus.get(item["sku_id"])
        if not sku:
            failed.append({"sku_id": str(item["sku_id"]), "requested": item["quantity"], "available": 0, "reason": "NOT_FOUND"})
            continue
        if sku.active_quantity < item["quantity"]:
            reason = "OUT_OF_STOCK" if sku.active_quantity == 0 else "INSUFFICIENT_STOCK"
            failed.append({"sku_id": str(sku.id), "requested": item["quantity"], "available": sku.active_quantity, "reason": reason})
        else:
            updates.append((sku, item["quantity"]))

    if failed:
        raise InsufficientStock(failed)

    out_of_stock_skus = []
    for sku, qty in updates:
        sku.active_quantity -= qty
        sku.reserved_quantity += qty
        session.add(sku)
        if sku.active_quantity == 0:
            out_of_stock_skus.append(sku)

    response = ReserveResponse(order_id=order_id, status="RESERVED", reserved_at=datetime.now(timezone.utc))
    reserve_op = ReserveOperation(idempotency_key=idempotency_key, result=response.model_dump(mode="json"))
    session.add(reserve_op)
    await session.commit()

    for sku in out_of_stock_skus:
        product = await session.get(Product, sku.product_id)
        if product:
            await send_sku_out_of_stock_event(sku)

    return response


async def unreserve_skus(
    session: AsyncSession,
    order_id: UUID,
    items: list[dict],
) -> InventoryOrderResponse:
    existing = await session.get(UnreserveOperation, order_id)
    if existing:
        return InventoryOrderResponse.model_validate(existing.result)

    sku_ids = sorted([item["sku_id"] for item in items])
    stmt = select(SKU).where(SKU.id.in_(sku_ids)).with_for_update()
    result = await session.execute(stmt)
    skus = {sku.id: sku for sku in result.scalars().all()}
    if len(skus) != len(sku_ids):
        missing = set(sku_ids) - set(skus.keys())
        raise SKUNotFound(f"SKU(s) {missing} not found")

    for item in items:
        sku = skus.get(item["sku_id"])
        if not sku:
            continue
        if sku.reserved_quantity < item["quantity"]:
            raise DomainException(code="INVALID_REQUEST", message=f"Not enough reserved quantity for SKU {sku.id}", status_code=409)

    for item in items:
        sku = skus[item["sku_id"]]
        sku.active_quantity += item["quantity"]
        sku.reserved_quantity -= item["quantity"]
        session.add(sku)

    response = InventoryOrderResponse(order_id=order_id, status="UNRESERVED", processed_at=datetime.now(timezone.utc))
    unreserve_op = UnreserveOperation(order_id=order_id, result=response.model_dump(mode="json"))
    session.add(unreserve_op)
    await session.commit()
    return response