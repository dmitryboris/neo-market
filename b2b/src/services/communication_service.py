from src.config import settings
import httpx
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.models import Product


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
