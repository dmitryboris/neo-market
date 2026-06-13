import httpx
from uuid import UUID
from src.config import settings
from src.services.exceptions import B2BServiceUnavailable


async def check_product_has_skus(product_id: UUID) -> bool:
    """Проверяет через B2B, есть ли у товара хотя бы один SKU. Возвращает True, если SKU есть."""
    url = f"{settings.B2B_URL}/api/v1/products/{product_id}"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            product_data = resp.json()
            return bool(product_data.get("skus"))
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable()


async def send_moderated_event(product_id: UUID) -> None:
    """Отправляет событие MODERATED в B2B."""
    url = f"{settings.B2B_URL}/api/v1/events/moderation"
    headers = {"X-Service-Key": settings.MOD_TO_B2B_KEY}
    payload = {"product_id": str(product_id), "status": "MODERATED"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise B2BServiceUnavailable(f"B2B error: {e.response.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise B2BServiceUnavailable("B2B service unavailable")
