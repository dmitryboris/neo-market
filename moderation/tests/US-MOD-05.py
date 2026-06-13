import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from src.models.ticket import Ticket, TicketStatus, TicketKind
from src.models.blocking_reason import BlockingReason


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
async def test_any_modify_on_hard_blocked_returns_409(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Любые мутирующие операции над HARD_BLOCKED возвращают 409."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.HARD_BLOCKED,
        claimed_by=moderator.id,
    )

    resp = await client.post(f"/api/v1/tickets/{ticket.id}/approve")
    assert resp.status_code == 409

    reason = await _create_blocking_reason(db_session, hard_block=False)
    resp = await client.post(
        f"/api/v1/tickets/{ticket.id}/block",
        json={"blocking_reason_ids": [str(reason.id)]},
    )
    assert resp.status_code == 409


