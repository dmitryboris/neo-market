import httpx
import uuid
from typing import Optional, Dict
from src.config import settings

async def _request(method: str, path: str, json=None) -> dict:
    url = f"{settings.B2B_URL}{path}"
    headers = {"X-Service-Key": settings.B2B_SERVICE_KEY}
    async with httpx.AsyncClient(timeout=2.0) as client:
        resp = await client.request(method, url, headers=headers, json=json)
        resp.raise_for_status()
        return resp.json()

async def check_sku(sku_id: uuid.UUID, quantity: int) -> dict:
    """Проверить SKU и остаток. Возвращает dict с product_id, name, price, active_quantity."""
    # TODO: реализовать вызов реального эндпоинта B2B для проверки SKU
    raise NotImplementedError()

async def batch_get_skus(sku_ids: list[uuid.UUID]) -> Dict[str, dict]:
    """Получить данные по нескольким SKU. Возвращает словарь {str(sku_id): {product_id, name, price, ...}}."""
    # TODO: реализовать batch-запрос к B2B
    raise NotImplementedError()