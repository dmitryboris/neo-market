import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from src.models.ticket import Ticket, TicketStatus, TicketKind
from src.models.moderator import Moderator
from src.models.blocking_reason import BlockingReason
from shared.enums import UserRole
from src.services.auth_service import hash_password


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
async def test_soft_block_transitions_to_blocked_with_field_reports(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Успешная мягкая блокировка: статус → BLOCKED, field_reports сохраняются."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=False)

    payload = {
        "blocking_reason_ids": [str(reason.id)],
        "comment": "Bad description",
        "field_reports": [
            {"field_path": "title", "message": "Misleading title"}
        ]
    }

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()) as mock_event:
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    # Проверяем отправку события
    mock_event.assert_called_once()
    call_kwargs = mock_event.call_args[1]
    assert call_kwargs["hard_block"] is False
    assert len(call_kwargs["reasons"]) == 1
    assert call_kwargs["reasons"][0]["id"] == str(reason.id)
    assert len(call_kwargs["field_reports"]) == 1


@pytest.mark.asyncio
async def test_soft_block_emits_event_to_b2b(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Событие BLOCKED + hard_block=false уходит в B2B."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=False)

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()) as mock_event:
        await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json={"blocking_reason_ids": [str(reason.id)]},
        )

    mock_event.assert_called_once()
    kwargs = mock_event.call_args[1]
    assert kwargs["hard_block"] is False
    assert kwargs["reasons"][0]["title"] == "Test reason"


@pytest.mark.asyncio
async def test_soft_block_unknown_reason_returns_400(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Несуществующий blocking_reason_id → 400."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )

    fake_reason_id = uuid4()
    payload = {"blocking_reason_ids": [str(fake_reason_id)]}

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json=payload,
        )

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert "Blocking reason not found" in data["message"]


@pytest.mark.asyncio
async def test_soft_block_others_card_returns_403(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Чужая карточка → 403."""
    client, _ = auth_client

    other_mod = Moderator(
        id=uuid4(),
        email="other_mod@example.com",
        first_name="Other",
        password_hash=hash_password("secret"),
        role=UserRole.MODERATOR,
        is_active=True,
    )
    db_session.add(other_mod)
    await db_session.flush()

    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=other_mod.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=False)

    payload = {"blocking_reason_ids": [str(reason.id)]}

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json=payload,
        )

    assert response.status_code == 403
    data = response.json()
    assert "not assigned" in data["message"].lower()


@pytest.mark.asyncio
async def test_soft_block_invalid_field_name_returns_400(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """field_reports[].field_name вне допустимого enum → 400."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session, uuid4(), uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )
    reason = await _create_blocking_reason(db_session, hard_block=False)

    payload = {
        "blocking_reason_ids": [str(reason.id)],
        "field_reports": [
            {"field_path": "invalid_field", "message": "Error"}
        ]
    }

    with patch("src.services.ticket_service.send_blocked_event", AsyncMock()):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/block",
            json=payload,
        )

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "INVALID_REQUEST"
    assert "field_path" in data["message"].lower()