import httpx
from uuid import UUID
from typing import Dict, List, Optional
from src.config import settings
from src.services.exceptions import SkuNotFound
from fastapi import HTTPException, status
from src.services.exceptions import B2BUnavailable

async def _request(method: str, path: str, json=None) -> dict:
    url = f"{settings.B2B_URL}{path}"
    headers = {"X-Service-Key": settings.B2C_TO_B2B_KEY}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.request(method, url, headers=headers, json=json)
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout):
        raise B2BUnavailable()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Resource not found"}
            )
        raise B2BUnavailable()

async def get_sku(sku_id: UUID) -> dict:
    """Получить информацию о SKU из B2B (публичный эндпоинт /api/v1/public/skus/{sku_id})."""
    try:
        data = await _request("GET", f"/api/v1/public/skus/{sku_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise SkuNotFound(f"SKU {sku_id} not found")
    return {
        "product_id": UUID(data["product_id"]),
        "name": data["name"],
        "price": data["price"],
        "active_quantity": data["active_quantity"],
        "sku_code": data.get("article"),
    }

async def batch_get_products(product_ids: List[UUID]) -> Dict[UUID, dict]:
    """
    Получить публичные данные о продуктах (со всеми SKU) через POST /api/v1/public/products/batch.
    Возвращает словарь {product_id: {status, skus: {sku_id: {price, active_quantity, name}}}}
    """
    if not product_ids:
        return {}
    payload = {"product_ids": [str(pid) for pid in product_ids]}
    products = await _request("POST", "/api/v1/public/products/batch", json=payload)
    result = {}
    for prod in products:
        prod_id = UUID(prod["id"])
        skus = {}
        for sku in prod.get("skus", []):
            sku_id = UUID(sku["id"])
            skus[sku_id] = {
                "price": sku["price"],
                "active_quantity": sku["active_quantity"],
                "name": sku["name"],
                "sku_code": sku.get("article"),
            }
        result[prod_id] = {
            "status": prod["status"],
            "skus": skus,
            "title": prod["title"],
        }
    return result


async def reserve_skus(idempotency_key: UUID, order_id: UUID, items: list[dict]) -> dict:
    """
    Вызывает POST /api/v1/inventory/reserve в B2B.
    Возвращает результат (успех или ошибку).
    При 409 возвращает словарь с reserved=False и failed_items.
    """
    payload = {
        "idempotency_key": str(idempotency_key),
        "order_id": str(order_id),
        "items": items,
    }
    try:
        return await _request("POST", "/api/v1/inventory/reserve", json=payload)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return e.response.json()
        
        if e.response.status_code == 503:
            raise B2BUnavailable()
        
        raise


async def unreserve_skus(order_id: UUID, items: list[dict]) -> dict:
    payload = {
        "order_id": str(order_id),
        "items": items,
    }

    return await _request(
        "POST",
        "/api/v1/inventory/unreserve",
        json=payload,
    )