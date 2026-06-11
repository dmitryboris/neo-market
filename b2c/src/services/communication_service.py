from fastapi import HTTPException
from src.config import settings
import httpx
from src.services.exceptions import ServiceUnavailable, InvalidSort



async def _request_b2b(method: str, path: str, json: dict = None, params: dict = None) -> dict | list:
    url = f"{settings.B2B_URL}{path}"
    headers = {"X-Service-Key": settings.B2C_TO_B2B_KEY}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            if method == "GET":
                resp = await client.get(url, params=params, headers=headers)
            else:
                resp = await client.post(url, json=json, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            detail = resp.json() if resp.headers.get("content-type") == "application/json" else {"code": "ERROR", "message": str(e)}
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except (httpx.ConnectError, httpx.TimeoutException):
            raise ServiceUnavailable()