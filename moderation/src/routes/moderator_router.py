from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user, require_admin_role
from src.models import Moderator
from shared.enums import UserRole
from src.schemas.moderator import (
    ModeratorCreateRequest,
    ModeratorUpdateRequest,
    ModeratorResponse,
    PaginatedModerators,
)
from src.services import moderator_service
from src.services.exceptions import DomainException

moderator_router = APIRouter(prefix="/moderators", tags=["Moderators"], dependencies=[Depends(require_admin_role)])


@moderator_router.get("", response_model=PaginatedModerators)
async def list_moderators(
        limit: int = 20,
        offset: int = 0,
        is_active: bool | None = Query(None),
        session: AsyncSession = Depends(get_session),
):
    return await moderator_service.list_moderators(session, limit, offset, is_active)


@moderator_router.post("", response_model=ModeratorResponse, status_code=status.HTTP_201_CREATED)
async def create_moderator(
        request: ModeratorCreateRequest,
        session: AsyncSession = Depends(get_session),
):
    return await moderator_service.create_moderator(session, request)


@moderator_router.get("/me", response_model=ModeratorResponse)
async def get_me(current: Moderator = Depends(get_current_user)):
    return ModeratorResponse.model_validate(current, from_attributes=True)


@moderator_router.get("/{moderator_id}", response_model=ModeratorResponse)
async def get_moderator(
        moderator_id: UUID,
        session: AsyncSession = Depends(get_session),
):
    return await moderator_service.get_moderator_by_id(session, moderator_id)


@moderator_router.patch("/{moderator_id}", response_model=ModeratorResponse)
async def update_moderator(
        moderator_id: UUID,
        request: ModeratorUpdateRequest,
        session: AsyncSession = Depends(get_session),
):
    return await moderator_service.update_moderator(session, moderator_id, request)


@moderator_router.delete("/{moderator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_moderator(
        moderator_id: UUID,
        session: AsyncSession = Depends(get_session),
):
    await moderator_service.delete_moderator(session, moderator_id)
    return None

