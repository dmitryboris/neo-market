from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import verify_b2b_service_key
from src.schemas.b2b import IncomingB2BEvent
from src.services import b2b_event_service

b2b_router = APIRouter(
    prefix="/b2b",
    tags=["B2B Events"],
    dependencies=[Depends(verify_b2b_service_key)],
)


@b2b_router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_b2b_event(
        event: IncomingB2BEvent,
        session: AsyncSession = Depends(get_session),
):
    await b2b_event_service.handle_incoming_event(
        session=session,
        event_type=event.event_type,
        idempotency_key=event.idempotency_key,
        payload=event.payload,
    )
