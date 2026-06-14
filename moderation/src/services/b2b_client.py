# moderation/src/services/b2b_client.py
import httpx
import uuid
from datetime import datetime, timezone
from uuid import UUID
from src.config import settings
from src.services.exceptions import B2BServiceUnavailable


async def check_product_has_skus(product_id: UUID) -> bool:
    """
    Проверяет через B2B, есть ли у товара хотя бы один SKU.
    Использует публичный эндпоинт B2B POST /api/v1/public/products/batch.
    """
    url = f"{settings.B2B_URL}/api/v1/public/products/batch"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    body = {"product_ids": [str(product_id)]}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            products = resp.json()
            if not products:
                return False
            return bool(products[0].get("skus"))
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()


async def send_moderated_event(product_id: UUID) -> None:
    """
    Отправляет событие MODERATED в B2B в соответствии с ModerationEventRequest.
    URL: /api/v1/moderation/events
    Обязательные поля: idempotency_key, product_id, event_type, occurred_at.
    """
    url = f"{settings.B2B_URL}/api/v1/moderation/events"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "product_id": str(product_id),
        "seller_id": None,
        "event_type": "MODERATED",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "moderator_id": None,
        "moderator_comment": None,
        "blocking_reason_id": None,
        "hard_block": False,
        "field_reports": [],
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
    """
    Отправляет событие BLOCKED в B2B в соответствии с ModerationEventRequest.
    URL: /api/v1/moderation/events
    Обязательные поля: idempotency_key, product_id, event_type, occurred_at.
    """
    url = f"{settings.B2B_URL}/api/v1/moderation/events"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "product_id": str(product_id),
        "seller_id": None,
        "event_type": "BLOCKED",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "moderator_id": None,
        "moderator_comment": "",
        "blocking_reason_id": reasons[0]["id"] if reasons else None,
        "hard_block": hard_block,
        "field_reports": field_reports,
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()