import httpx
import uuid
from datetime import datetime, timezone
from uuid import UUID
from src.config import settings
from src.services.exceptions import B2BServiceUnavailable, ProductNotFound


async def get_product(product_id: UUID) -> dict:
    """Получает полные данные товара из B2B (seller endpoint)."""
    url = f"{settings.B2B_URL}/api/v1/products/{product_id}"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                raise ProductNotFound()
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()


async def check_product_has_skus(product_id: UUID) -> bool:
    url = f"{settings.B2B_URL}/api/v1/products/{product_id}"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            product = resp.json()
            return bool(product.get("skus"))
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()


async def send_moderated_event(product_id: UUID) -> None:
    url = f"{settings.B2B_URL}/api/v1/moderation/events"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "product_id": str(product_id),
        "event_type": "MODERATED",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable("B2B service unavailable")


async def send_blocked_event(
        product_id: UUID,
        hard_block: bool,
        reasons: list[dict],
        field_reports: list[dict],
) -> None:
    url = f"{settings.B2B_URL}/api/v1/moderation/events"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "product_id": str(product_id),
        "event_type": "BLOCKED",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "blocking_reason_id": reasons[0]["id"] if reasons else None,
        "hard_block": hard_block,
        "field_reports": field_reports,
    }
    # Убираем None-значения, чтобы не засорять payload
    payload = {k: v for k, v in payload.items() if v is not None}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()
