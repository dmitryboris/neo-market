from src.config import settings
import httpx
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Product, ProductStatus, SKU, FieldReport, ProcessedModerationEvent
from src.services.exceptions import (
    ProductNotFound, IdempotencyKeyMissing, ProductIdMissing, EventTypeMissing,
    InvalidModerationEvent, BlockingReasonIdMissing, FieldReportsMissing
)
from src.schemas.moderation import ModerationEventType

async def apply_moderation_event(
    session: AsyncSession,
    idempotency_key: UUID,
    product_id: UUID,
    event_type: str,
    hard_block: bool,
    blocking_reason_id: UUID | None,
    field_reports_data: list[dict],
) -> None:
    SENDER_SERVICE = "moderation"

    if idempotency_key is None:
        raise IdempotencyKeyMissing()
    if product_id is None:
        raise ProductIdMissing()
    if event_type is None:
        raise EventTypeMissing()

    stmt = select(ProcessedModerationEvent).where(
        ProcessedModerationEvent.sender_service == SENDER_SERVICE,
        ProcessedModerationEvent.idempotency_key == idempotency_key
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        age = datetime.now(timezone.utc) - existing.processed_at
        if age < timedelta(hours=24):
            return
        else:
            await session.delete(existing)
            await session.flush()
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFound()
    
    if event_type == "BLOCKED":
        if blocking_reason_id is None:
            raise BlockingReasonIdMissing()
        if field_reports_data is None:
            raise FieldReportsMissing()

    if event_type == ModerationEventType.MODERATED:
        product.status = ProductStatus.MODERATED
        product.blocked = False
        product.blocking_reason_id = None
        await session.execute(
            delete(FieldReport).where(FieldReport.product_id == product.id)
        )
    elif event_type == ModerationEventType.BLOCKED:
        if hard_block:
            product.status = ProductStatus.HARD_BLOCKED
        else:
            product.status = ProductStatus.BLOCKED
        product.blocked = True

        if blocking_reason_id:
            product.blocking_reason_id = blocking_reason_id

        await session.execute(
            delete(FieldReport).where(FieldReport.product_id == product.id)
        )
        for fr in field_reports_data:
            field_report = FieldReport(
                product_id=product.id,
                sku_id=fr.get("sku_id"),
                field_name=fr["field_name"],
                comment=fr["comment"],
            )
            session.add(field_report)

        sku_active = await session.execute(
            select(SKU.id).where(
                SKU.product_id == product.id,
                SKU.active_quantity > 0
            )
        )
        sku_ids = [row[0] for row in sku_active.fetchall()]
        if sku_ids:
            await _send_b2c_event(product, sku_ids, event_type="PRODUCT_BLOCKED")
    else:
        raise InvalidModerationEvent()

    processed = ProcessedModerationEvent(
        sender_service=SENDER_SERVICE,
        idempotency_key=idempotency_key
    )
    session.add(processed)
    await session.commit()


async def _send_moderation_event(product: Product, event_type: str = "CREATED") -> None:
    """Фоновый вызов Moderation API (fire-and-forget)"""
    url = f"{settings.MODERATION_URL}/api/v1/events/product"
    headers = {"X-Service-Key": settings.B2B_TO_MOD_KEY}
    idempotency_key = str(uuid4())
    payload = {
        "idempotency_key": idempotency_key,
        "product_id": str(product.id),
        "seller_id": str(product.seller_id),
        "event": event_type,
        "date": datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
    }
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Failed to send moderation event: {e}")


async def _send_b2c_event(product: Product, sku_ids: list[UUID], event_type: str = "PRODUCT_DELETED") -> None:
    """Фоновый вызов Moderation API (fire-and-forget)"""

    url = f"{settings.B2C_URL}/api/v1/events/product"
    headers = {"X-Service-Key": settings.B2B_TO_B2C_KEY}
    payload = {
        "idempotency_key": str(uuid4()),
        "event": event_type,
        "product_id": str(product.id),
        "sku_ids": [str(sku_id) for sku_id in sku_ids],
        "date": datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
    }
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Failed to send B2C event: {e}")


async def send_sku_out_of_stock_event(sku: SKU, event_type: str = "SKU_OUT_OF_STOCK") -> None:
    """Отправляет событие SKU_OUT_OF_STOCK в B2C."""
    url = f"{settings.B2C_URL}/api/v1/b2b/events"
    headers = {"X-Service-Key": settings.B2B_TO_B2C_KEY}
    payload = {
        "event_type": event_type,
        "idempotency_key": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        "payload": {
            "sku_id": str(sku.id),
            "product_id": str(sku.product_id),
            "available_quantity": 0
        }
    }
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(url, json=payload, headers=headers)
        except Exception as e:
            print(f"Failed to send SKU_OUT_OF_STOCK event: {e}")