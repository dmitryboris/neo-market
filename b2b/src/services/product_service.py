from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional, List
from src.models import Product, Category, ProductImage, ProductCharacteristic, SKU
from src.schemas.product import ProductCreateRequest, ProductUpdateRequest
from src.services.exceptions import CategoryNotFound, ProductNotFound, AccessDenied

async def get_product_by_id(
    session: AsyncSession,
    product_id: UUID,
    seller_id: Optional[UUID] = None
) -> Product:
    """Получить товар по ID. Если передан seller_id – проверить принадлежность."""
    stmt = select(Product).where(Product.id == product_id)
    if seller_id:
        stmt = stmt.where(Product.seller_id == seller_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    if seller_id and product.seller_id != seller_id:
        raise AccessDenied("You do not have access to this product")
    return product

async def get_my_products(
    session: AsyncSession,
    seller_id: UUID,
    limit: int = 20,
    offset: int = 0
) -> dict:
    """Список товаров продавца с пагинацией."""
    total_result = await session.execute(
        select(func.count(Product.id)).where(Product.seller_id == seller_id)
    )
    total = total_result.scalar_one()
    stmt = select(Product).where(Product.seller_id == seller_id).order_by(Product.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    products = result.scalars().all()
    return {"total": total, "items": products}

async def create_product(
    session: AsyncSession,
    seller_id: UUID,
    request: ProductCreateRequest
) -> Product:
    cat_result = await session.execute(select(Category).where(Category.id == request.category_id))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise CategoryNotFound(f"Category {request.category_id} not found")

    product = Product(
        seller_id=seller_id,
        category_id=request.category_id,
        title=request.title,
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
    request: ProductUpdateRequest
) -> Product:
    """Обновить поля товара (category, title, description, status)."""
    if request.category_id is not None:
        cat_result = await session.execute(select(Category).where(Category.id == request.category_id))
        category = cat_result.scalar_one_or_none()
        if not category:
            raise CategoryNotFound(f"Category {request.category_id} not found")
        product.category_id = request.category_id
    if request.title is not None:
        product.title = request.title
    if request.description is not None:
        product.description = request.description
    if request.status is not None:
        product.status = request.status
    await session.commit()
    await session.refresh(product, attribute_names=["images", "characteristics", "skus", "category"])
    return product

async def delete_product(session: AsyncSession, product: Product) -> None:
    """Удалить товар (каскадно удалятся изображения, характеристики, SKU)."""
    await session.delete(product)
    await session.commit()