import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.models.ticket import Ticket, TicketStatus, TicketKind
from src.schemas.b2b import B2BEventType
from src.services.exceptions import (
    DomainException,
    DuplicateEvent,
    TicketNotFound,
)
from src.services.b2b_client import get_product

_idempotency_store: dict[uuid.UUID, datetime] = {}
_lock = __import__('threading').Lock()


async def handle_incoming_event(
    session: AsyncSession,
    event_type: B2BEventType,
    idempotency_key: uuid.UUID,
    payload,
) -> None:
    now = datetime.now(timezone.utc)
    with _lock:
        expired = [k for k, t in _idempotency_store.items() if now - t > timedelta(hours=24)]
        for k in expired:
            del _idempotency_store[k]
        if idempotency_key in _idempotency_store:
            return
        _idempotency_store[idempotency_key] = now

    if event_type == B2BEventType.PRODUCT_CREATED:
        await _handle_created(session, payload)
    elif event_type == B2BEventType.PRODUCT_EDITED:
        await _handle_edited(session, payload)
    elif event_type == B2BEventType.PRODUCT_DELETED:
        await _handle_deleted(session, payload)
    else:
        raise DomainException(code="INVALID_REQUEST", message=f"Unknown event type: {event_type}", status_code=400)


async def _handle_created(session: AsyncSession, payload) -> None:
    stmt = select(Ticket).where(Ticket.product_id == payload.product_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status == TicketStatus.HARD_BLOCKED:
            return
        raise DuplicateEvent("Ticket already exists for this product")

    product_data = await get_product(payload.product_id)

    ticket = Ticket(
        product_id=payload.product_id,
        seller_id=payload.seller_id,
        category_id=payload.category_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.PENDING,
        queue_priority=payload.queue_priority,
        json_after=product_data,
    )
    session.add(ticket)
    await session.flush()


async def _handle_edited(session: AsyncSession, payload) -> None:
    stmt = select(Ticket).where(Ticket.product_id == payload.product_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise TicketNotFound("Ticket not found for EDIT event")

    if ticket.status == TicketStatus.HARD_BLOCKED:
        return

    old_status = ticket.status

    product_data = await get_product(payload.product_id)

    ticket.json_before = ticket.json_after
    ticket.json_after = product_data
    ticket.status = TicketStatus.PENDING

    if old_status in (TicketStatus.BLOCKED, TicketStatus.APPROVED):
        ticket.queue_priority = _calc_priority(old_status, product_data)

    ticket.claimed_by = None
    ticket.claimed_at = None
    ticket.claim_expires_at = None
    ticket.moderator_comment = None
    ticket.field_reports = []

    session.add(ticket)
    await session.flush()


async def _handle_deleted(session: AsyncSession, payload) -> None:
    stmt = delete(Ticket).where(Ticket.product_id == payload.product_id)
    await session.execute(stmt)
    await session.flush()


def _calc_priority(old_status: str, product_data: dict) -> int:
    """Вычисляет queue_priority по правилам EDITED."""
    if old_status == TicketStatus.BLOCKED:
        return 2
    if old_status == TicketStatus.APPROVED:
        total_active = sum(
            sku.get("active_quantity", 0) for sku in product_data.get("skus", [])
        )
        return 3 if total_active > 0 else 4
    return 3