from uuid import UUID
from sqlalchemy import select
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Ticket, TicketStatus, BlockingReason, Moderator
from src.schemas.ticket import TicketResponse, ApproveRequest, BlockDecisionRequest
from src.services.exceptions import (
    TicketNotFound,
    TicketNotInReview,
    TicketHardBlocked,
    NotAssignedToModerator,
    TicketHasNoSKUs,
    B2BServiceUnavailable,
    BlockingReasonNotFound,
    TicketHardBlockedModify
)
from src.services.b2b_client import check_product_has_skus, send_moderated_event, send_blocked_event
from shared.exceptions import DomainException


async def approve_ticket(
        ticket_id: UUID,
        moderator: Moderator,
        request: ApproveRequest | None = None,
        session: AsyncSession = None,
) -> TicketResponse:
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise TicketNotFound()

    if ticket.status == TicketStatus.HARD_BLOCKED:
        raise TicketHardBlocked()
    if ticket.status != TicketStatus.IN_REVIEW:
        raise TicketNotInReview()

    if ticket.claimed_by != moderator.id:
        raise NotAssignedToModerator()

    has_skus = await check_product_has_skus(ticket.product_id)

    if not has_skus:
        raise TicketHasNoSKUs()

    await send_moderated_event(ticket.product_id)

    ticket.status = TicketStatus.APPROVED
    ticket.decision_at = datetime.now(timezone.utc)
    comment = request.comment if request else None
    ticket.moderator_comment = comment
    ticket.field_reports = []

    await session.commit()
    await session.refresh(ticket)

    return TicketResponse.model_validate(ticket, from_attributes=True)


async def block_ticket(
        ticket_id: UUID,
        moderator: Moderator,
        request: BlockDecisionRequest,
        session: AsyncSession = None,
) -> TicketResponse:
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise TicketNotFound()

    if ticket.status == TicketStatus.HARD_BLOCKED:
        raise TicketHardBlocked()
    if ticket.status != TicketStatus.IN_REVIEW:
        raise TicketNotInReview()
    if ticket.claimed_by != moderator.id:
        raise NotAssignedToModerator()

    VALID_FIELD_NAMES = {
        "title", "description", "product_images", "category",
        "sku_name", "sku_image", "sku_price"
    }
    if request.field_reports:
        for report in request.field_reports:
            if report.field_name not in VALID_FIELD_NAMES:
                raise DomainException(
                    code="INVALID_REQUEST",
                    message=f"Invalid field_name: {report.field_name}. "
                            f"Allowed: {', '.join(sorted(VALID_FIELD_NAMES))}",
                    status_code=400,
                )

    stmt = select(BlockingReason).where(BlockingReason.id.in_(request.blocking_reason_ids))
    result = await session.execute(stmt)
    reasons = result.scalars().all()
    if len(reasons) != len(request.blocking_reason_ids):
        raise BlockingReasonNotFound()

    hard_block = any(r.hard_block for r in reasons)

    reason_data = [
        {
            "id": str(r.id),
            "title": r.title,
            "comment": r.description or ""
        } for r in reasons
    ]

    main_reason_id = reasons[0].id if reasons else None

    await send_blocked_event(
        product_id=ticket.product_id,
        hard_block=hard_block,
        reasons=reason_data,
        field_reports=[r.model_dump() for r in request.field_reports] if request.field_reports else []
    )

    ticket.status = TicketStatus.HARD_BLOCKED if hard_block else TicketStatus.BLOCKED
    ticket.decision_at = datetime.now(timezone.utc)
    ticket.blocking_reason_id = main_reason_id
    ticket.moderator_comment = request.comment
    ticket.field_reports = [r.model_dump() for r in request.field_reports]

    await session.commit()
    await session.refresh(ticket)

    return TicketResponse.model_validate(ticket, from_attributes=True)
