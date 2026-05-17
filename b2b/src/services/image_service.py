from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.services.exceptions import (
    ProductNotFound, SKUNotFound, ImageNotFound, NoFieldsToUpdate
)
from src.services.file_service import delete_file_from_disk
from src.models.sku import SKU
from src.models.sku_image import SKUImage
from src.models.product_image import ProductImage
from src.models.product import Product


async def _get_product_with_access(session: AsyncSession, product_id: UUID, seller_id: UUID) -> Product:
    result = await session.execute(
        select(Product)
        .where(Product.id == product_id, Product.seller_id == seller_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFound("Product not found or access denied")
    return product


async def _get_sku_with_access(session: AsyncSession, sku_id: UUID, seller_id: UUID) -> SKU:
    result = await session.execute(
        select(SKU)
        .join(Product, SKU.product_id == Product.id)
        .where(SKU.id == sku_id, Product.seller_id == seller_id)
    )
    sku = result.scalar_one_or_none()
    if not sku:
        raise SKUNotFound("SKU not found or access denied")
    return sku


async def _get_product_image_with_access(session: AsyncSession, image_id: UUID, seller_id: UUID) -> ProductImage:
    result = await session.execute(
        select(ProductImage)
        .join(Product, ProductImage.product_id == Product.id)
        .where(ProductImage.id == image_id, Product.seller_id == seller_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise ImageNotFound("Product image not found or access denied")
    return image


async def _get_sku_image_with_access(session: AsyncSession, image_id: UUID, seller_id: UUID) -> SKUImage:
    result = await session.execute(
        select(SKUImage)
        .join(SKU, SKUImage.sku_id == SKU.id)
        .join(Product, SKU.product_id == Product.id)
        .where(SKUImage.id == image_id, Product.seller_id == seller_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise ImageNotFound("SKU image not found or access denied")
    return image


async def add_product_image(
        session: AsyncSession,
        product_id: UUID,
        seller_id: UUID,
        url: str,
        ordering: int = 0
) -> ProductImage:
    await _get_product_with_access(session, product_id, seller_id)
    image = ProductImage(product_id=product_id, url=url, ordering=ordering)
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return image


async def update_product_image(
        session: AsyncSession,
        image_id: UUID,
        seller_id: UUID,
        url: str | None = None,
        ordering: int | None = None
) -> ProductImage:
    if url is None and ordering is None:
        raise NoFieldsToUpdate("At least one field (url or ordering) must be provided")
    image = await _get_product_image_with_access(session, image_id, seller_id)
    if url is not None:
        image.url = url
    if ordering is not None:
        image.ordering = ordering
    await session.commit()
    await session.refresh(image)
    return image


async def update_product_image_ordering(
        session: AsyncSession,
        image_id: UUID,
        ordering: int,
        seller_id: UUID
) -> ProductImage:
    return await update_product_image(
        session=session, image_id=image_id,
        seller_id=seller_id, ordering=ordering
    )


async def delete_product_image(session: AsyncSession, image_id: UUID, seller_id: UUID):
    image = await _get_product_image_with_access(session, image_id, seller_id)
    url = image.url
    await session.delete(image)
    await session.commit()
    delete_file_from_disk(url)


# ----- public API for SKU images -----
async def add_sku_image(
        session: AsyncSession,
        sku_id: UUID,
        seller_id: UUID, url: str,
        ordering: int = 0
) -> SKUImage:
    await _get_sku_with_access(session, sku_id, seller_id)
    image = SKUImage(sku_id=sku_id, url=url, ordering=ordering)
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return image


async def update_sku_image(
        session: AsyncSession,
        image_id: UUID,
        seller_id: UUID,
        url: str | None = None,
        ordering: int | None = None
) -> SKUImage:
    if url is None and ordering is None:
        raise NoFieldsToUpdate("At least one field (url or ordering) must be provided")
    image = await _get_sku_image_with_access(session, image_id, seller_id)
    if url is not None:
        image.url = url
    if ordering is not None:
        image.ordering = ordering
    await session.commit()
    await session.refresh(image)
    return image


async def update_sku_image_ordering(
        session: AsyncSession,
        image_id: UUID,
        ordering: int,
        seller_id: UUID
) -> SKUImage:
    return await update_sku_image(
        session=session, image_id=image_id,
        seller_id=seller_id, ordering=ordering
    )


async def delete_sku_image(session: AsyncSession, image_id: UUID, seller_id: UUID):
    image = await _get_sku_image_with_access(session, image_id, seller_id)
    url = image.url
    await session.delete(image)
    await session.commit()
    delete_file_from_disk(url)
