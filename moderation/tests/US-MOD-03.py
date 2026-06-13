# moderation/tests/US-MOD-03.py
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from src.models.ticket import Ticket, TicketStatus, TicketKind
from src.models.moderator import Moderator
from shared.enums import UserRole
from src.services.auth_service import hash_password


async def _create_ticket(
    db_session,
    product_id: UUID,
    seller_id: UUID,
    *,
    status: TicketStatus = TicketStatus.IN_REVIEW,
    claimed_by: UUID | None = None,
    **kwargs,
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
        **kwargs,
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


@pytest.mark.asyncio
async def test_approve_transitions_to_moderated_and_emits_event(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Успешное одобрение: статус → APPROVED, событие MODERATED отправлено."""
    client, moderator = auth_client

    product_id = uuid4()
    seller_id = uuid4()
    ticket = await _create_ticket(
        db_session,
        product_id,
        seller_id,
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )

    with patch(
        "src.services.ticket_service.check_product_has_skus", return_value=True
    ), patch(
        "src.services.ticket_service.send_moderated_event", AsyncMock()
    ) as mock_send_event:
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
            json={"comment": "Looks good"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["claimed_by"] == str(moderator.id)
    assert data["decision_at"] is not None

    mock_send_event.assert_called_once_with(ticket.product_id)

    await db_session.refresh(ticket)
    assert ticket.status == TicketStatus.APPROVED
    assert ticket.field_reports == []


@pytest.mark.asyncio
async def test_approve_others_card_returns_403(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Модератор не может одобрить тикет, закреплённый за другим."""
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
        db_session,
        product_id=uuid4(),
        seller_id=uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=other_mod.id,
    )

    with patch("src.services.ticket_service.check_product_has_skus", return_value=True):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
        )

    assert response.status_code == 403
    data = response.json()
    assert "not assigned" in data["message"].lower()


@pytest.mark.asyncio
async def test_approve_after_edited_returns_409(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Тикет, который уже не в статусе IN_REVIEW (например, после редактирования
    продавцом), нельзя одобрить — 409 Conflict."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session,
        uuid4(),
        uuid4(),
        status=TicketStatus.PENDING,
        claimed_by=moderator.id,
    )

    with patch("src.services.ticket_service.check_product_has_skus", return_value=True):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
        )

    assert response.status_code == 409
    data = response.json()
    assert "not in review" in data["message"].lower()


@pytest.mark.asyncio
async def test_approve_without_sku_returns_409(
    client: AsyncClient,
    db_session,
    auth_client,
):
    """Если B2B сообщает, что у товара нет SKU, одобрение невозможно (409)."""
    client, moderator = auth_client
    ticket = await _create_ticket(
        db_session,
        uuid4(),
        uuid4(),
        status=TicketStatus.IN_REVIEW,
        claimed_by=moderator.id,
    )

    with patch(
        "src.services.ticket_service.check_product_has_skus", return_value=False
    ):
        response = await client.post(
            f"/api/v1/tickets/{ticket.id}/approve",
        )

    assert response.status_code == 409
    data = response.json()
    assert "no skus" in data["message"].lower() or "sku" in data["message"].lower()