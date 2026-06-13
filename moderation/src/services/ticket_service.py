from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.ticket import Ticket, TicketStatus
from src.models.moderator import Moderator
from src.schemas.ticket import TicketResponse, ApproveRequest
from src.services.exceptions import (
    TicketNotFound,
    TicketNotInReview,
    TicketHardBlocked,
    NotAssignedToModerator,
    TicketHasNoSKUs,
    B2BServiceUnavailable,
)
from src.services.b2b_client import check_product_has_skus, send_moderated_event


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
