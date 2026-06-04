import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from src.models import SKU, Product, ProductStatus, SKUImage, SKUCharacteristic
from src.schemas.sku import SKUCreate, SKUUpdate
from src.services.exceptions import (
    ProductNotFound, ProductHardBlocked, SKUNameEmpty, SKUNameInvalid,
    SKUImageNotFound, SKUPriceInvalid, SKUCostPriceInvalid
)
from src.config import settings
import httpx
from datetime import datetime, timezone


async def get_product_with_access(session: AsyncSession, product_id: uuid.UUID, seller_id: uuid.UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFound()
    return product


async def _send_moderation_event(product: Product, event_type: str = "CREATED") -> None:
    """Фоновый вызов Moderation API (fire-and-forget)"""
    url = f"{settings.MODERATION_URL}/api/v1/events/product"
    headers = {"X-Service-Key": settings.B2B_TO_MOD_KEY}
    idempotency_key = str(uuid.uuid4())
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


async def create_sku(
        session: AsyncSession,
        seller_id: uuid.UUID,
        request: SKUCreate
) -> SKU:
    product = await get_product_with_access(session, request.product_id, seller_id)

    if product.status == ProductStatus.HARD_BLOCKED:
        raise ProductHardBlocked()

    if not request.name or not request.name.strip():
        raise SKUNameEmpty()
    if len(request.name) > 255:
        raise SKUNameInvalid()
    if not request.images or len(request.images) == 0:
        raise SKUImageNotFound()
    if request.price is None or request.price <= 0:
        raise SKUPriceInvalid()
    if request.cost_price is None or request.cost_price <= 0:
        raise SKUCostPriceInvalid()

    count_result = await session.execute(
        select(func.count()).select_from(SKU).where(SKU.product_id == request.product_id)
    )
    sku_count = count_result.scalar()

    sku = SKU(
        product_id=request.product_id,
        name=request.name,
        price=request.price,
        cost_price=request.cost_price,
        discount=request.discount,
        active_quantity=0,
        reserved_quantity=0,
        stock_quantity=0,
        article=request.article,
    )
    session.add(sku)
    await session.flush()

    for idx, img in enumerate(request.images):
        sku_image = SKUImage(sku_id=sku.id, url=img.url, ordering=img.ordering)
        session.add(sku_image)

    for ch in request.characteristics:
        char = SKUCharacteristic(
            sku_id=sku.id,
            name=ch.name,
            value=ch.value
        )
        session.add(char)

    if sku_count == 0:
        product.status = ProductStatus.ON_MODERATION
        session.add(product)
        asyncio.create_task(_send_moderation_event(product, event_type="CREATED"))
    else:
        if product.status in (ProductStatus.MODERATED, ProductStatus.BLOCKED):
            product.status = ProductStatus.ON_MODERATION
            asyncio.create_task(_send_moderation_event(product, event_type="EDITED"))

    await session.commit()
    await session.refresh(sku, attribute_names=["images", "characteristics"])
    return sku


async def get_sku_by_id(session: AsyncSession, sku_id: uuid.UUID, seller_id: uuid.UUID | None = None) -> SKU | None:
    stmt = select(SKU).options(
        selectinload(SKU.images),
        selectinload(SKU.characteristics),
    ).where(SKU.id == sku_id)
    if seller_id:
        stmt = stmt.join(Product).where(Product.seller_id == seller_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_skus_by_product(session: AsyncSession, product_id: uuid.UUID, seller_id: uuid.UUID) -> list[SKU]:
    product = await get_product_with_access(session, product_id, seller_id)
    result = await session.execute(
        select(SKU)
        .options(selectinload(SKU.images), selectinload(SKU.characteristics))
        .where(SKU.product_id == product_id)
    )
    return result.scalars().all()


async def update_sku(session: AsyncSession, sku: SKU, request: SKUUpdate) -> SKU:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(sku, field, value)
    await session.commit()
    return await get_sku_by_id(session, sku.id)


async def delete_sku(session: AsyncSession, sku: SKU) -> None:
    await session.delete(sku)
    await session.commit()
