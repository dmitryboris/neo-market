from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import UUID, select
from sqlalchemy.orm import selectinload
from src.models import Category, Product
from src.schemas.category import CategoryCreate, CategoryUpdate
from src.services.exceptions import (
    CategoryParentNotFound,
    CategorySelfParentError,
    CategoryHasProducts,
    CategoryHasChildren,
)


async def get_category_by_id(session: AsyncSession, category_id) -> Category | None:
    result = await session.execute(
        select(Category)
        .options(
            selectinload(Category.children),
            selectinload(Category.parent)
        )
        .where(Category.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_categories(session: AsyncSession, parent_id: UUID | None = None, only_root: bool = False) -> list[Category]:
    query = select(Category).options(selectinload(Category.children))
    if only_root:
        query = query.where(Category.parent_id == None)
    elif parent_id is not None:
        query = query.where(Category.parent_id == parent_id)

    result = await session.execute(query)
    return result.scalars().all()


async def create_category(session: AsyncSession, request: CategoryCreate) -> Category:
    if request.parent_id:
        parent = await get_category_by_id(session, request.parent_id)
        if not parent:
            raise CategoryParentNotFound("Parent category not found")

    category = Category(
        name=request.name,
        parent_id=request.parent_id,
    )
    session.add(category)
    await session.commit()

    return await get_category_by_id(session, category.id)


async def update_category(session: AsyncSession, category: Category, request: CategoryUpdate) -> Category:
    if request.parent_id:
        if request.parent_id == category.id:
            raise CategorySelfParentError("Category cannot be its own parent")
        parent = await get_category_by_id(session, request.parent_id)
        if not parent:
            raise CategoryParentNotFound("Parent category not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await session.commit()

    return await get_category_by_id(session, category.id)


async def delete_category(session: AsyncSession, category: Category):
    product_exists = await session.scalar(
        select(Product.id).where(Product.category_id == category.id).limit(1)
    )
    if product_exists:
        raise CategoryHasProducts("Category contains products and cannot be deleted")
    
    child_exists = await session.scalar(
        select(Category.id).where(Category.parent_id == category.id).limit(1)
    )
    if child_exists:
        raise CategoryHasChildren("Category contains subcategories and cannot be deleted")
    
    await session.delete(category)
    await session.commit()