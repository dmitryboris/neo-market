from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithChildrenResponse, CategoryTreeResponse
from src.services import category_service
from src.services import exceptions as exc

category_router = APIRouter(prefix="/categories", tags=["Categories"])


@category_router.get("", response_model=list[CategoryResponse], summary="List categories")
async def get_categories(
        parent_id: UUID | None = None,
        only_root: bool = False,
        session: AsyncSession = Depends(get_session)
):
    return await category_service.get_categories(session, parent_id, only_root)


@category_router.get("/{category_id}", response_model=CategoryWithChildrenResponse,
                     summary="Get category with subcategories")
async def get_category(
        category_id: UUID,
        session: AsyncSession = Depends(get_session)
):
    category = await category_service.get_category_by_id(session, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category_service.serialize_category_with_children(category)


@category_router.post(
    "",
    response_model=CategoryWithChildrenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category"
)
async def create_category(
        request: CategoryCreate,
        session: AsyncSession = Depends(get_session),
        _: None = Depends(get_current_user)
):
    try:
        return await category_service.create_category(session, request)
    except exc.CategoryParentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@category_router.patch(
    "/{category_id}",
    response_model=CategoryWithChildrenResponse,
    summary="Update category"
)
async def update_category(
        category_id: UUID,
        request: CategoryUpdate,
        session: AsyncSession = Depends(get_session),
        _: None = Depends(get_current_user)
):
    category = await category_service.get_category_by_id(session, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    try:
        return await category_service.update_category(session, category, request)
    except exc.CategoryParentNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except exc.CategorySelfParentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@category_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
)
async def delete_category(
        category_id: UUID,
        session: AsyncSession = Depends(get_session),
        _: None = Depends(get_current_user),
):
    category = await category_service.get_category_by_id(session, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    try:
        await category_service.delete_category(session, category)
    except exc.CategoryHasProducts as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except exc.CategoryHasChildren as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@category_router.get(
    "/tree",
    response_model=list[CategoryTreeResponse],
    summary="Get category tree"
)
async def get_categories_tree(session: AsyncSession = Depends(get_session)):
    return await category_service.get_categories_tree(session)


@category_router.get(
    "/{category_id}/breadcrumbs",
    response_model=list[CategoryResponse],
    summary="Get category breadcrumbs"
)
async def get_category_breadcrumbs(
    category_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    return await category_service.get_breadcrumbs(session, category_id)