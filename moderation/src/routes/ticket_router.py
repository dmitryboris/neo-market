from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from src.schemas.ticket import ApproveRequest, TicketResponse, BlockDecisionRequest
from src.services import ticket_service
from src.models import Moderator

ticket_router = APIRouter(prefix="/tickets", tags=["Tickets"])


@ticket_router.post("/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket(
        ticket_id: UUID,
        request: ApproveRequest | None = None,
        session: AsyncSession = Depends(get_session),
        current_moderator: Moderator = Depends(get_current_user),
):
    return await ticket_service.approve_ticket(
        ticket_id=ticket_id,
        moderator=current_moderator,
        request=request,
        session=session,
    )


@ticket_router.post("/{ticket_id}/block", response_model=TicketResponse)
async def block_ticket(
        ticket_id: UUID,
        request: BlockDecisionRequest,
        session: AsyncSession = Depends(get_session),
        current_moderator: Moderator = Depends(get_current_user),
):
    return await ticket_service.block_ticket(
        ticket_id=ticket_id,
        moderator=current_moderator,
        request=request,
        session=session,
    )
