from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from uuid import UUID
from src.models import Product, Category, ProductImage, ProductCharacteristic, SKU
from src.schemas.product import (
    ProductCreate, ProductUpdate, ProductShortResponse, ProductPaginatedResponse, ProductStatus,
    ProductPublicShortResponse, ProductPublicPaginatedResponse
)
from src.services.exceptions import (
    CategoryNotFound, ProductNotFound, AccessDenied, ProductTitleEmpty,
    CategoryInvalid, ProductTitleInvalid, ProductImageNotFound, UUIDInvalid,
    ProductHardBlocked, NotOwner, ProductAlreadyDeleted
)
from sqlalchemy.orm import selectinload
from src.services.communication_service import _send_moderation_event, _send_b2c_event


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
    if not product:
        raise ProductNotFound()
    if seller_id is not None and product.seller_id != seller_id:
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
        seller_id: UUID,
        request: ProductUpdate
) -> Product:
    """Обновить поля товара (category, title, description, status)."""
    if seller_id != product.seller_id:
        raise NotOwner()

    if product.status == ProductStatus.HARD_BLOCKED:
        raise ProductHardBlocked()

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


async def delete_product(
        session: AsyncSession,
        seller_id: UUID,
        product: Product
) -> None:
    if seller_id != product.seller_id:
        raise NotOwner()

    if product.deleted:
        raise ProductAlreadyDeleted()
    
    if product.status == ProductStatus.HARD_BLOCKED:
        raise ProductHardBlocked() 

    product.deleted = True
    sku_ids = [sku.id for sku in product.skus]

    await _send_moderation_event(product, "DELETED")
    await _send_b2c_event(product, sku_ids, "PRODUCT_DELETED")

    await session.commit()


async def list_public_products(
    session: AsyncSession,
    category_id: UUID | None = None,
    search: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    seller_id: UUID | None = None,
    sort: str = "created_desc",
    limit: int = 20,
    offset: int = 0,
    filters: dict | None = None,
) -> tuple[list[Product], int]:
    """
    Возвращает пагинированный список публичных товаров и общее количество.
    Условия видимости: status = MODERATED, deleted = False,
    существует хотя бы один SKU с active_quantity > 0.
    """
    stmt = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.characteristics),
        selectinload(Product.skus).selectinload(SKU.images),
        selectinload(Product.skus).selectinload(SKU.characteristics),
    ).where(
        Product.status == ProductStatus.MODERATED,
        Product.deleted == False,
        Product.id.in_(
            select(SKU.product_id).where(SKU.active_quantity > 0)
        )
    )

    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    if seller_id:
        stmt = stmt.where(Product.seller_id == seller_id)

    if search:
        stmt = stmt.where(
            or_(
                Product.title.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )

    if min_price is not None or max_price is not None:
        price_subq = select(SKU.product_id).where(SKU.active_quantity > 0)
        if min_price is not None:
            price_subq = price_subq.where(SKU.price >= min_price)
        if max_price is not None:
            price_subq = price_subq.where(SKU.price <= max_price)
        stmt = stmt.where(Product.id.in_(price_subq.subquery()))

    if sort == "price_asc":
        min_price_subq = select(
            SKU.product_id, func.min(SKU.price).label("min_price")
        ).where(SKU.active_quantity > 0).group_by(SKU.product_id).subquery()
        stmt = stmt.outerjoin(
            min_price_subq, Product.id == min_price_subq.c.product_id
        ).order_by(min_price_subq.c.min_price.asc(), Product.id)
    elif sort == "price_desc":
        min_price_subq = select(
            SKU.product_id, func.min(SKU.price).label("min_price")
        ).where(SKU.active_quantity > 0).group_by(SKU.product_id).subquery()
        stmt = stmt.outerjoin(
            min_price_subq, Product.id == min_price_subq.c.product_id
        ).order_by(min_price_subq.c.min_price.desc(), Product.id)
    elif sort == "created_desc":
        stmt = stmt.order_by(Product.created_at.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    if filters:
        for name, values in filters.items():
            if not isinstance(values, list):
                values = [values]
            subq = select(ProductCharacteristic.product_id).where(
                ProductCharacteristic.name == name,
                ProductCharacteristic.value.in_(values)
            ).distinct()
            stmt = stmt.where(Product.id.in_(subq))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt)

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    products = result.scalars().all()
    items = []
    for p in products:
        min_price_val = min((sku.price for sku in p.skus if sku.active_quantity > 0), default=0)
        cover_image = p.images[0].url if p.images else None
        items.append(ProductPublicShortResponse(
            id=p.id,
            title=p.title,
            slug=p.slug,
            status=p.status,
            category_id=p.category_id,
            min_price=min_price_val,
            cover_image=cover_image,
            created_at=p.created_at,
        ))

    return ProductPublicPaginatedResponse(
        items=items,
        total_count=total,
        limit=limit,
        offset=offset,
    )

async def get_public_products_by_ids(
    session: AsyncSession,
    product_ids: list[UUID]
) -> list[Product]:
    """
    Возвращает товары из списка IDs, которые удовлетворяют условиям видимости.
    """
    if not product_ids:
        return []
    stmt = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.characteristics),
        selectinload(Product.skus).selectinload(SKU.images),
        selectinload(Product.skus).selectinload(SKU.characteristics),
    ).where(
        Product.id.in_(product_ids),
        Product.status == ProductStatus.MODERATED,
        Product.deleted == False,
        Product.id.in_(
            select(SKU.product_id).where(SKU.active_quantity > 0)
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()