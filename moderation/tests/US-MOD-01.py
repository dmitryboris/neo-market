import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID

from src.config import settings
from src.models.ticket import Ticket, TicketStatus, TicketKind
from src.schemas.b2b import B2BEventType
from src.services.b2b_event_service import _idempotency_store, _lock


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


@pytest.fixture(autouse=True)
def clear_idempotency_store():
    """Очищает in-memory хранилище перед каждым тестом."""
    with _lock:
        _idempotency_store.clear()
    yield
    with _lock:
        _idempotency_store.clear()


@pytest.mark.asyncio
async def test_created_event_creates_pending_ticket(client: AsyncClient, db_session):
    """PRODUCT_CREATED создаёт тикет в статусе PENDING."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    payload = _event_payload(
        B2BEventType.PRODUCT_CREATED,
        product_id=product_id,
        seller_id=seller_id,
    )

    with patch(
        "src.services.b2b_event_service.get_product", return_value=MOCK_PRODUCT
    ):
        response = await client.post(
            "/api/v1/b2b/events",
            json=payload,
            headers=_b2b_headers(),
        )

    assert response.status_code == 202

    stmt = select(Ticket).where(Ticket.product_id == product_id)
    result = await db_session.execute(stmt)
    ticket = result.scalar_one_or_none()
    assert ticket is not None
    assert ticket.status == TicketStatus.PENDING
    assert ticket.kind == TicketKind.CREATE
    assert ticket.seller_id == UUID(seller_id)


@pytest.mark.asyncio
async def test_edited_event_after_moderated_returns_to_pending(
    client: AsyncClient, db_session
):
    """EDITED после MODERATED/BLOCKED возвращает тикет в PENDING с обновлённым приоритетом."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.APPROVED,
        queue_priority=2,
        json_after={"title": "old"},
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    payload = _event_payload(
        B2BEventType.PRODUCT_EDITED,
        product_id=product_id,
        seller_id=seller_id,
        json_before=ticket.json_after,
        json_after={"title": "new"},
    )

    with patch(
        "src.services.b2b_event_service.get_product", return_value=MOCK_PRODUCT
    ):
        response = await client.post(
            "/api/v1/b2b/events",
            json=payload,
            headers=_b2b_headers(),
        )

    assert response.status_code == 202

    await db_session.refresh(ticket)
    assert ticket.status == TicketStatus.PENDING
    assert ticket.queue_priority == 3
    assert ticket.json_before == {"title": "old"}
    assert ticket.json_after == MOCK_PRODUCT


@pytest.mark.asyncio
async def test_edited_event_updates_in_review(
    client: AsyncClient, db_session
):
    """EDITED во время IN_REVIEW обновляет поля, приоритет сохраняется."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.IN_REVIEW,
        queue_priority=2,
        json_after={"title": "old"},
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    payload = _event_payload(
        B2BEventType.PRODUCT_EDITED,
        product_id=product_id,
        seller_id=seller_id,
        json_before=ticket.json_after,
        json_after={"title": "new"},
    )

    with patch(
        "src.services.b2b_event_service.get_product", return_value=MOCK_PRODUCT
    ):
        response = await client.post(
            "/api/v1/b2b/events",
            json=payload,
            headers=_b2b_headers(),
        )

    assert response.status_code == 202

    await db_session.refresh(ticket)
    assert ticket.status == TicketStatus.PENDING
    assert ticket.queue_priority == 2
    assert ticket.json_before == {"title": "old"}
    assert ticket.json_after == MOCK_PRODUCT


@pytest.mark.asyncio
async def test_deleted_event_removes_ticket(client: AsyncClient, db_session):
    """PRODUCT_DELETED удаляет тикет из очереди."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    ticket = Ticket(
        product_id=product_id,
        seller_id=seller_id,
        kind=TicketKind.CREATE,
        status=TicketStatus.IN_REVIEW,
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


@pytest.mark.asyncio
async def test_duplicate_event_no_side_effects(client: AsyncClient, db_session):
    """Повторное событие с тем же ключом идемпотентности → 202 без изменений."""
    product_id = str(uuid4())
    seller_id = str(uuid4())
    id_key = str(uuid4())
    payload = _event_payload(
        B2BEventType.PRODUCT_CREATED,
        idempotency_key=id_key,
        product_id=product_id,
        seller_id=seller_id,
    )

    with patch(
        "src.services.b2b_event_service.get_product", return_value=MOCK_PRODUCT
    ):
        resp1 = await client.post(
            "/api/v1/b2b/events", json=payload, headers=_b2b_headers()
        )
        assert resp1.status_code == 202

        resp2 = await client.post(
            "/api/v1/b2b/events", json=payload, headers=_b2b_headers()
        )
        assert resp2.status_code == 202

    stmt = select(Ticket).where(Ticket.product_id == product_id)
    result = await db_session.execute(stmt)
    tickets = result.scalars().all()
    assert len(tickets) == 1


@pytest.mark.asyncio
async def test_missing_service_header_returns_401(client: AsyncClient):
    """Запрос без X-Service-Key → 401."""
    payload = _event_payload(B2BEventType.PRODUCT_CREATED)

    response = await client.post("/api/v1/b2b/events", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"