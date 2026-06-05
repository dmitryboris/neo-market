import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from src.models import SKU, Product, ProductStatus, SKUImage, SKUCharacteristic
from src.schemas.sku import SKUCreate, SKUUpdate
from src.services.exceptions import (
    ProductNotFound, ProductHardBlocked, SKUNameEmpty, SKUNameInvalid,
    SKUImageNotFound, SKUPriceInvalid, SKUCostPriceInvalid, SKUNotFound, UUIDInvalid
)
from src.config import settings
import httpx
from src.services.communication_service import _send_moderation_event


async def get_product_with_access(session: AsyncSession, product_id: UUID, seller_id: UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFound()
    return product


async def create_sku(
        session: AsyncSession,
        seller_id: UUID,
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


async def get_sku_by_id(
        session: AsyncSession,
        sku_id: str,
        seller_id: UUID
) -> SKU:
    """Получить SKU по ID. Если передан seller_id – проверить принадлежность."""
    try:
        _ = UUID(sku_id)
    except (ValueError, AttributeError, TypeError):
        raise UUIDInvalid()

    stmt = (
        select(SKU)
        .where(SKU.id == sku_id)
        .options(
            selectinload(SKU.product),
            selectinload(SKU.images),
            selectinload(SKU.characteristics),
        )
    )
    result = await session.execute(stmt)
    sku = result.scalar_one_or_none()

    if not sku or sku.product.seller_id != seller_id:
        raise SKUNotFound()
    return sku


async def update_sku(
        session: AsyncSession,
        sku: SKU,
        request: SKUUpdate
) -> SKU:
    """Обновить SKU с валидацией и побочными эффектами на товаре."""

    product = sku.product
    if product.status == ProductStatus.HARD_BLOCKED:
        raise ProductHardBlocked("Cannot edit hard-blocked product")

    if request.name is not None:
        if not request.name.strip():
            raise SKUNameEmpty()
        if len(request.name) > 255:
            raise SKUNameInvalid()
        sku.name = request.name

    if request.price is not None:
        if request.price <= 0:
            raise SKUPriceInvalid()
        sku.price = request.price

    if request.discount is not None:
        sku.discount = request.discount

    if request.cost_price is not None:
        if request.cost_price <= 0:
            raise SKUCostPriceInvalid()
        sku.cost_price = request.cost_price

    if request.article is not None:
        sku.article = request.article

    if request.characteristics is not None:
        for old_ch in sku.characteristics:
            await session.delete(old_ch)
        for ch in request.characteristics:
            new_ch = SKUCharacteristic(
                sku_id=sku.id,
                name=ch.name,
                value=ch.value,
            )
            session.add(new_ch)

    await session.flush()

    if product.status in (ProductStatus.MODERATED, ProductStatus.BLOCKED):
        product.status = ProductStatus.ON_MODERATION
        await _send_moderation_event(product, "EDITED")

    await session.commit()
    await session.refresh(sku, attribute_names=["images", "characteristics", "product"])

    return await get_sku_by_id(session, str(sku.id), sku.product.seller_id)


async def delete_sku(session: AsyncSession, sku: SKU) -> None:
    await session.delete(sku)
    await session.commit()
