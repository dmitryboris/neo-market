from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from src.models import Product, Category, ProductImage, ProductCharacteristic, SKU
from src.schemas.product import (
    ProductCreate, ProductUpdate, ProductShortResponse, ProductPaginatedResponse, ProductStatus
)
from src.services.exceptions import (
    CategoryNotFound, ProductNotFound, AccessDenied, ProductTitleEmpty,
    CategoryInvalid, ProductTitleInvalid, ProductImageNotFound, UUIDInvalid,
    ProductHardBlocked
)
from sqlalchemy.orm import selectinload
from src.services.communication_service import _send_moderation_event


async def get_product_by_id(
        session: AsyncSession,
        product_id: str,
        seller_id: UUID | None = None,
) -> Product:
    """Получить товар по ID. Если передан seller_id – проверить принадлежность."""
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise UUIDInvalid()
    
    stmt = select(Product).where(Product.id == product_uuid).options(
        selectinload(Product.images),
        selectinload(Product.characteristics),
        selectinload(Product.skus).selectinload(SKU.images),
        selectinload(Product.skus).selectinload(SKU.characteristics),
        selectinload(Product.blocking_reason),
        selectinload(Product.field_reports)
    )
    
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product or (seller_id is not None and product.seller_id != seller_id):
        raise ProductNotFound()
    return product


async def get_my_products(
        session: AsyncSession,
        seller_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status: ProductStatus | None = None,
        include_deleted: bool = False,
) -> ProductPaginatedResponse:
    query = select(Product).where(Product.seller_id == seller_id)
    if status:
        query = query.where(Product.status == status)
    if not include_deleted:
        query = query.where(Product.deleted == False)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query.options(selectinload(Product.images)))
    items = result.scalars().all()
    short_items = [ProductShortResponse.model_validate(p) for p in items]
    return ProductPaginatedResponse(
        total_count=total,
        items=short_items,
        limit=limit,
        offset=offset,
    )


async def create_product(
        session: AsyncSession,
        seller_id: UUID,
        request: ProductCreate,
        category_uuid: UUID
) -> Product:
    if not request.title or not request.title.strip():
        raise ProductTitleEmpty()
    if len(request.title) < 1 or len(request.title) > 255:
        raise ProductTitleInvalid()
    if request.category_id is None:
        raise CategoryNotFound()
    if not request.images:
        raise ProductImageNotFound()

    try:
        _ = UUID(str(request.category_id))
    except (ValueError, AttributeError, TypeError):
        raise CategoryInvalid()

    cat_result = await session.execute(select(Category).where(Category.id == category_uuid))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise CategoryNotFound()

    product = Product(
        seller_id=seller_id,
        category_id=category_uuid,
        title=request.title,
        slug=request.slug,
        description=request.description,
        status="CREATED"
    )
    session.add(product)
    await session.flush()

    for img in request.images:
        product_image = ProductImage(
            product_id=product.id,
            url=img.url,
            ordering=img.ordering
        )
        session.add(product_image)

    for ch in request.characteristics:
        char = ProductCharacteristic(
            product_id=product.id,
            name=ch.name,
            value=ch.value
        )
        session.add(char)

    await session.commit()
    await session.refresh(product, attribute_names=["images", "characteristics", "skus", "category"])
    return product


async def update_product(
        session: AsyncSession,
        product: Product,
        request: ProductUpdate
) -> Product:
    """Обновить поля товара (category, title, description, status)."""

    if product.status == ProductStatus.HARD_BLOCKED:
        raise ProductHardBlocked("Cannot edit hard-blocked product")

    if request.title is not None:
        if not request.title.strip():
            raise ProductTitleEmpty()
        if len(request.title) < 1 or len(request.title) > 255:
            raise ProductTitleInvalid()
        product.title = request.title

    if request.category_id is not None:
        try:
            category_uuid = UUID(request.category_id)
        except (ValueError, AttributeError, TypeError):
            raise CategoryInvalid()
        cat_result = await session.execute(
            select(Category).where(Category.id == category_uuid)
        )
        if not cat_result.scalar_one_or_none():
            raise CategoryNotFound()
        product.category_id = category_uuid

    if request.description is not None:
        product.description = request.description

    if request.characteristics is not None:
        for existing_char in product.characteristics:
            await session.delete(existing_char)
        for ch in request.characteristics:
            new_char = ProductCharacteristic(
                product_id=product.id,
                name=ch.name,
                value=ch.value
            )
            session.add(new_char)

    if product.status in (ProductStatus.MODERATED, ProductStatus.BLOCKED):
        product.status = ProductStatus.ON_MODERATION
        await _send_moderation_event(product, "EDITED")

    await session.commit()
    await session.refresh(product, attribute_names=["images", "characteristics", "skus", "category"])
    return await get_product_by_id(session, str(product.id))


async def delete_product(session: AsyncSession, product: Product) -> None:
    """Удалить товар (каскадно удалятся изображения, характеристики, SKU)."""
    await session.delete(product)
    await session.commit()
