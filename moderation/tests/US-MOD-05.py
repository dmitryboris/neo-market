import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select

from src.models import Ticket, TicketStatus, TicketKind, BlockingReason
from src.config import settings
from src.schemas.b2b import B2BEventType


def _b2b_headers() -> dict[str, str]:
    """Заголовок для межсервисной авторизации."""
    return {"X-Service-Key": settings.B2B_TO_MOD_KEY}


def _event_payload(
        event_type: B2BEventType,
        idempotency_key: str | None = None,
        product_id: str | None = None,
        seller_id: str | None = None,
        **kwargs,
) -> dict:
    payload = {
        "product_id": product_id or str(uuid4()),
        "seller_id": seller_id or str(uuid4()),
        "category_id": str(uuid4()) if kwargs.get("category_id") else None,
        "queue_priority": kwargs.get("queue_priority", 3),
    }
    if event_type == B2BEventType.PRODUCT_CREATED:
        payload["json_after"] = kwargs.get("json_after", {})
    elif event_type == B2BEventType.PRODUCT_EDITED:
        payload["json_before"] = kwargs.get("json_before", {})
        payload["json_after"] = kwargs.get("json_after", {})
    return {
        "event_type": event_type,
        "idempotency_key": idempotency_key or str(uuid4()),
        "occurred_at": "2026-06-15T00:00:00Z",
        "payload": payload,
    }


MOCK_PRODUCT = {
    "title": "Test",
    "description": "Desc",
    "skus": [{"id": str(uuid4()), "active_quantity": 5}],
}


async def _create_ticket(
        db_session,
        product_id: UUID,
        seller_id: UUID,
        *,
        status: TicketStatus = TicketStatus.IN_REVIEW,
        claimed_by: UUID | None = None,
) -> Ticket:
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=status,
        queue_priority=3,
        claimed_by=claimed_by,
        claimed_at=datetime.now(timezone.utc) if claimed_by else None,
        json_after={"title": "Test product"},
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


async def _create_blocking_reason(
        db_session,
        hard_block: bool = False,
        *,
        code: str = "test_reason",
        title: str = "Test reason",
) -> BlockingReason:
    reason = BlockingReason(
        id=uuid4(),
        code=code,
        title=title,
        description="Description",
        hard_block=hard_block,
        is_active=True,
    )
    db_session.add(reason)
    await db_session.commit()
    return reason


@pytest.mark.asyncio
async def test_hard_block_transitions_to_terminal_and_emits_event(
        client: AsyncClient,
        db_session,
        auth_client,
):
    """Жёсткая блокировка: статус → HARD_BLOCKED, событие BLOCKED + hard_block=true."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=True)

    payload = {"blocking_reason_ids": [str(reason.id)]}

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()) as mock_event:
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HARD_BLOCKED"

    mock_event.assert_called_once()
    kwargs = mock_event.call_args[1]
    assert kwargs["hard_block"] is True


@pytest.mark.asyncio
async def test_hard_block_event_carries_hard_block_true(
        client: AsyncClient,
        db_session,
        auth_client,
):
    """Флаг hard_block=true в событии."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=True)

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()) as mock_event:
        await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json={"blocking_reason_ids": [str(reason.id)]},
        )

    mock_event.assert_called_once()
    assert mock_event.call_args[1]["hard_block"] is True


@pytest.mark.asyncio
async def test_any_modify_on_hard_blocked_returns_403(
        client: AsyncClient,
        db_session,
        auth_client,
):
    """Любые мутирующие операции над HARD_BLOCKED возвращают 403."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.HARD_BLOCKED,
        claimed_by=moderator.id,
    )

    resp = await client.post(f"/api/v1/tickets/{ticket.id}/approve")
    assert resp.status_code == 403

    reason = await _create_blocking_reason(db_session, hard_block=False)
    resp = await client.post(
        f"/api/v1/tickets/{ticket.id}/block",
        json={"blocking_reason_ids": [str(reason.id)]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_edited_event_on_hard_blocked_is_ignored(
        client, db_session,
):
    """EDITED событие от B2B не выводит HARD_BLOCKED тикет из терминала."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.HARD_BLOCKED,
    )
    db_session.add(ticket)
    await db_session.commit()

    payload = _event_payload(
        B2BEventType.PRODUCT_EDITED,
        product_id=product_id,
        seller_id=seller_id,
        json_before={},
        json_after={"title": "new"},
    )

    with patch("src.services.b2b_event_service.get_product", return_value=MOCK_PRODUCT):
        response = await client.post(
            "/api/v1/b2b/events",
            json=payload,
            headers=_b2b_headers(),
        )

    assert response.status_code == 202
    await db_session.refresh(ticket)
    assert ticket.status == TicketStatus.HARD_BLOCKED


@pytest.mark.asyncio
async def test_deleted_event_removes_hard_blocked(
        client, db_session,
):
    """PRODUCT_DELETED удаляет HARD_BLOCKED тикет из Moderation."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.HARD_BLOCKED,
    )
    db_session.add(ticket)
    await db_session.commit()

    payload = _event_payload(
        B2BEventType.PRODUCT_DELETED,
        product_id=product_id,
        seller_id=seller_id,
    )

    response = await client.post(
        "/api/v1/b2b/events",
        json=payload,
        headers=_b2b_headers(),
    )

    assert response.status_code == 202

    stmt = select(Ticket).where(Ticket.product_id == product_id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None
