import pytest
from uuid import uuid4
from src.models import Product, ProductStatus, BlockingReason, FieldReport, SKU, Category
from tests.conftest import TEST_SELLER_ID
from src.config import settings
from sqlalchemy import select
from src.schemas.moderation import ModerationEventType


@pytest.fixture
async def blocking_reason(db_session):
    reason = BlockingReason(
        id=uuid4(),
        title="Test Reason",
        comment="Test comment"
    )
    db_session.add(reason)
    await db_session.commit()
    return reason


@pytest.fixture
async def product_for_moderation(db_session):
    category = Category(
        id=uuid4(),
        name="Test Category for Moderation"
    )
    db_session.add(category)
    await db_session.flush()

    prod = Product(
        id=uuid4(),
        seller_id=TEST_SELLER_ID,
        category_id=category.id,
        title="Moderation Test",
        slug="mod-test",
        description="Test",
        status=ProductStatus.ON_MODERATION,
    )
    db_session.add(prod)
    await db_session.commit()
    return prod

@pytest.mark.asyncio
async def test_moderated_event_clears_blocking_data(client, product_for_moderation, db_session):
    reason = BlockingReason(id=uuid4(), title="Reason", comment="Comment")
    db_session.add(reason)
    product_for_moderation.status = ProductStatus.BLOCKED
    product_for_moderation.blocking_reason = reason
    field = FieldReport(product_id=product_for_moderation.id, field_name="title", comment="Bad")
    db_session.add(field)
    await db_session.commit()

    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.MODERATED,
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 204
    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.MODERATED
    assert product_for_moderation.blocking_reason_id is None
    reports = await db_session.execute(select(FieldReport).where(FieldReport.product_id == product_for_moderation.id))
    assert reports.scalars().all() == []

@pytest.mark.asyncio
async def test_blocked_soft_saves_field_reports(client, product_for_moderation, db_session, blocking_reason):
    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.BLOCKED,
        "hard_block": False,
        "blocking_reason_id": str(blocking_reason.id),
        "field_reports": [
            {"field_name": "title", "comment": "Misleading title", "sku_id": None}
        ],
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 204
    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.BLOCKED
    assert product_for_moderation.blocked is True
    assert product_for_moderation.blocking_reason_id == blocking_reason.id
    reports = await db_session.execute(select(FieldReport).where(FieldReport.product_id == product_for_moderation.id))
    reports_list = reports.scalars().all()
    assert len(reports_list) == 1
    assert reports_list[0].field_name == "title"

@pytest.mark.asyncio
async def test_blocked_hard_sets_terminal_status(client, product_for_moderation, db_session, blocking_reason):
    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.BLOCKED,
        "hard_block": True,
        "blocking_reason_id": str(blocking_reason.id),
        "field_reports": [],
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 204
    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.HARD_BLOCKED

@pytest.mark.asyncio
async def test_duplicate_event_idempotency(client, product_for_moderation, db_session):
    reason = BlockingReason(
        id=uuid4(),
        title="Test reason",
        comment="For idempotency test"
    )
    db_session.add(reason)
    await db_session.commit()
    key = str(uuid4())
    event = {
        "idempotency_key": key,
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.BLOCKED,
        "hard_block": False,
        "blocking_reason_id": str(reason.id),
        "field_reports": [{"field_name": "title", "comment": "Bad"}],
        "occurred_at": "2024-01-01T00:00:00Z"
    }

    resp1 = await client.post("/api/v1/moderation/events", json=event, headers={"X-Service-Key": settings.B2B_TO_MOD_KEY})
    assert resp1.status_code == 204
    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.BLOCKED
    updated_at1 = product_for_moderation.updated_at

    resp2 = await client.post("/api/v1/moderation/events", json=event, headers={"X-Service-Key": settings.B2B_TO_MOD_KEY})
    assert resp2.status_code == 204
    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.BLOCKED
    assert product_for_moderation.updated_at == updated_at1

@pytest.mark.asyncio
async def test_missing_service_key_returns_401(client, product_for_moderation):
    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.MODERATED,
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post("/api/v1/moderation/events", json=event)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hard_blocked_product_rejects_seller_edits(client, db_session, product_for_moderation):
    reason = BlockingReason(id=uuid4(), title="Hard block reason", comment="Terminal")
    db_session.add(reason)
    await db_session.commit()
    reason_id = reason.id

    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": ModerationEventType.BLOCKED,
        "hard_block": True,
        "blocking_reason_id": str(reason_id),
        "field_reports": [],
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    resp_event = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert resp_event.status_code == 204

    await db_session.refresh(product_for_moderation)
    assert product_for_moderation.status == ProductStatus.HARD_BLOCKED

    update_resp = await client.patch(
        f"/api/v1/products/{product_for_moderation.id}",
        json={"title": "New Title"}
    )
    assert update_resp.status_code == 403
    assert "hard-blocked" in update_resp.text.lower()

    delete_resp = await client.delete(
        f"/api/v1/products/{product_for_moderation.id}"
    )
    assert delete_resp.status_code == 403
    assert "hard-blocked" in delete_resp.text.lower()

@pytest.mark.asyncio
async def test_missing_idempotency_key_returns_400(client, product_for_moderation):
    event = {
        "product_id": str(product_for_moderation.id),
        "event_type": "MODERATED",
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "idempotency_key is required" in response.json()["message"]

@pytest.mark.asyncio
async def test_missing_product_id_returns_400(client):
    event = {
        "idempotency_key": str(uuid4()),
        "event_type": "MODERATED",
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "product_id is required" in response.json()["message"]

@pytest.mark.asyncio
async def test_invalid_event_type_returns_400(client, product_for_moderation):
    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": "INVALID",
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "Unknown event_type" in response.json()["message"]

@pytest.mark.asyncio
async def test_blocked_missing_blocking_reason_returns_400(client, product_for_moderation):
    event = {
        "idempotency_key": str(uuid4()),
        "product_id": str(product_for_moderation.id),
        "event_type": "BLOCKED",
        "hard_block": False,
        "field_reports": [],
        "occurred_at": "2024-01-01T00:00:00Z"
    }
    response = await client.post(
        "/api/v1/moderation/events",
        json=event,
        headers={"X-Service-Key": settings.B2B_TO_MOD_KEY}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "blocking_reason_id is required" in response.json()["message"]
