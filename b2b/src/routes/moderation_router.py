from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import require_moderation_key
from src.schemas.moderation import ModerationEventRequest
from src.services.communication_service import apply_moderation_event

moderation_router = APIRouter(prefix="/moderation", tags=["Moderation Events"], dependencies=[Depends(require_moderation_key)])

@moderation_router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def receive_moderation_event(
    request: ModerationEventRequest,
    session: AsyncSession = Depends(get_session),
):
    await apply_moderation_event(
        session=session,
        idempotency_key=request.idempotency_key,
        product_id=request.product_id,
        event_type=request.event_type,
        hard_block=request.hard_block,
        blocking_reason_id=request.blocking_reason_id,
        field_reports_data=[fr.model_dump() for fr in request.field_reports] if request.field_reports else []
    )
    return None