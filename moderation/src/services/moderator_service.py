from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.moderator import Moderator
from src.schemas.moderator import (
    ModeratorCreateRequest,
    ModeratorUpdateRequest,
    ModeratorResponse,
    PaginatedModerators,
)
from src.services.exceptions import EmailAlreadyExists, ModeratorNotFound
from shared.security import hash_password


async def list_moderators(
        session: AsyncSession,
        limit: int,
        offset: int,
        is_active: bool | None = None,
) -> PaginatedModerators:
    stmt = select(Moderator)
    count_stmt = select(func.count(Moderator.id))
    if is_active is not None:
        stmt = stmt.where(Moderator.is_active == is_active)
        count_stmt = count_stmt.where(Moderator.is_active == is_active)
    stmt = stmt.limit(limit).offset(offset).order_by(Moderator.email)

    result = await session.execute(stmt)
    items = result.scalars().all()
    total = await session.execute(count_stmt)
    total_count = total.scalar_one()

    moderator_responses = [ModeratorResponse.model_validate(m, from_attributes=True) for m in items]
    return PaginatedModerators(
        items=moderator_responses,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


async def create_moderator(
        session: AsyncSession,
        request: ModeratorCreateRequest,
) -> ModeratorResponse:
    stmt = select(Moderator).where(Moderator.email == request.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise EmailAlreadyExists()

    moderator = Moderator(
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role,
        is_active=True,
        # category_specializations=data.category_specializations,
    )
    session.add(moderator)
    await session.commit()
    await session.refresh(moderator)
    return ModeratorResponse.model_validate(moderator, from_attributes=True)


async def get_moderator_by_id(
        session: AsyncSession,
        moderator_id: UUID,
) -> ModeratorResponse:
    moderator = await session.get(Moderator, moderator_id)
    if not moderator:
        raise ModeratorNotFound()
    return ModeratorResponse.model_validate(moderator, from_attributes=True)


async def update_moderator(
        session: AsyncSession,
        moderator_id: UUID,
        data: ModeratorUpdateRequest,
) -> ModeratorResponse:
    moderator = await session.get(Moderator, moderator_id)
    if not moderator:
        raise ModeratorNotFound()

    if data.first_name is not None:
        moderator.first_name = data.first_name
    if data.last_name is not None:
        moderator.last_name = data.last_name
    if data.is_active is not None:
        moderator.is_active = data.is_active
    if data.role is not None:
        moderator.role = data.role
    # if data.category_specializations is not None:
    #     moderator.category_specializations = data.category_specializations

    await session.commit()
    await session.refresh(moderator)
    return ModeratorResponse.model_validate(moderator, from_attributes=True)


async def delete_moderator(
        session: AsyncSession,
        moderator_id: UUID,
) -> None:
    moderator = await session.get(Moderator, moderator_id)
    if not moderator:
        raise ModeratorNotFound()
    moderator.is_active = False
    await session.commit()
