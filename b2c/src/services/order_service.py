# src/services/order_service.py

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Order, OrderItem as OrderItemModel, OrderStatus, Address, PaymentMethod
from src.schemas.order import OrderResponse, OrderItem as OrderItemSchema, AddressResponse, PaymentMethodResponse
from src.services.cart_service import enrich_cart, get_or_create_cart
from src.services.b2b_client import reserve_skus
from src.services.exceptions import CartInvalidException, CartMismatchException, ReserveFailed, B2BUnavailable


async def create_order(
    session: AsyncSession,
    buyer_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    address_id: uuid.UUID,
    payment_method_id: uuid.UUID,
    comment: Optional[str] = None,
    items_snapshot: Optional[List[dict]] = None,
) -> OrderResponse:
    existing = await session.execute(
        select(Order)
        .where(Order.idempotency_key == idempotency_key)
        .options(selectinload(Order.address), selectinload(Order.payment_method))
    )
    existing_order = existing.scalar_one_or_none()
    if existing_order:
        return _order_to_response(existing_order)

    cart = await get_or_create_cart(session, user_id=buyer_id)
    enriched_cart = await enrich_cart(session, cart)

    if not enriched_cart.items:
        raise CartInvalidException({
            "is_valid": False,
            "cart": enriched_cart.model_dump(),
            "issues": [{"sku_id": None, "type": "EMPTY_CART", "message": "Cart is empty"}]
        })
    if not enriched_cart.is_valid:
        validation_response = {
            "is_valid": False,
            "cart": enriched_cart.model_dump(),
            "issues": _build_validation_issues(enriched_cart)
        }
        raise CartInvalidException(validation_response)

    if items_snapshot is not None:
        snapshot_map = {str(i["sku_id"]): i for i in items_snapshot}
        for item in enriched_cart.items:
            snap = snapshot_map.get(str(item.sku_id))
            if not snap or snap["quantity"] != item.quantity or snap["unit_price"] != item.unit_price:
                raise CartMismatchException()

    address = await session.get(Address, address_id)
    if not address or address.buyer_id != buyer_id:
        raise DomainException(code="INVALID_ADDRESS", message="Address not found or not owned", status_code=404)

    payment_method = await session.get(PaymentMethod, payment_method_id)
    if not payment_method or payment_method.buyer_id != buyer_id:
        raise DomainException(code="INVALID_PAYMENT_METHOD", message="Payment method not found or not owned", status_code=404)

    reserve_items = [{"sku_id": str(item.sku_id), "quantity": item.quantity} for item in enriched_cart.items]
    try:
        reserve_result = await reserve_skus(idempotency_key, reserve_items)
    except Exception as e:
        if isinstance(e, B2BUnavailable):
            raise
        raise B2BUnavailable() from e

    if not reserve_result.get("reserved", False):
        raise ReserveFailed(reserve_result.get("failed_items", []))

    total_amount = 0
    order = Order(
        user_id=buyer_id,
        status=OrderStatus.PAID,
        total_amount=0,
        idempotency_key=idempotency_key,
        address_id=address_id,
        payment_method_id=payment_method_id,
        comment=comment,
    )
    session.add(order)
    await session.flush()

    for item in enriched_cart.items:
        line_total = item.unit_price * item.quantity
        total_amount += line_total
        order_item = OrderItemModel(
            order_id=order.id,
            sku_id=item.sku_id,
            product_id=item.product_id,
            product_title=item.name,
            sku_name=item.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=line_total,
        )
        session.add(order_item)

    order.total_amount = total_amount
    await session.commit()

    await session.refresh(order, attribute_names=["address", "payment_method", "items_rel"])
    return _order_to_response(order)


def _build_validation_issues(enriched_cart) -> list[dict]:
    """Формирует список проблем из CartResponse.is_valid=False"""
    issues = []
    for item in enriched_cart.items:
        if not item.is_available:
            reason = "OUT_OF_STOCK" if item.available_quantity == 0 else "PRODUCT_BLOCKED"
            issues.append({
                "sku_id": str(item.sku_id),
                "type": reason,
                "message": f"SKU {item.sku_id} is not available",
                "old_value": None,
                "new_value": None,
            })
        elif item.quantity > item.available_quantity:
            issues.append({
                "sku_id": str(item.sku_id),
                "type": "QUANTITY_REDUCED",
                "message": f"Requested {item.quantity}, available {item.available_quantity}",
                "old_value": item.quantity,
                "new_value": item.available_quantity,
            })
    return issues


def _order_to_response(order: Order) -> OrderResponse:
    """Преобразует SQLAlchemy Order в Pydantic OrderResponse"""
    items = []
    for item in order.items_rel:
        items.append(OrderItemSchema(
            sku_id=item.sku_id,
            product_id=item.product_id,
            name=f"{item.product_title} {item.sku_name}".strip(),
            sku_code=None,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            image_url=None,
        ))
    return OrderResponse(
        id=order.id,
        number=None,
        buyer_id=order.user_id,
        status=order.status,
        status_history=None,
        items=items,
        subtotal=sum(i.line_total for i in items),
        delivery_cost=0,
        total=order.total_amount,
        address=AddressResponse(
            id=order.address.id,
            created_at=order.address.created_at,
            country=order.address.country,
            region=order.address.region,
            city=order.address.city,
            street=order.address.street,
            building=order.address.building,
            apartment=order.address.apartment,
            postal_code=order.address.postal_code,
            recipient_name=order.address.recipient_name,
            recipient_phone=order.address.recipient_phone,
            is_default=order.address.is_default,
            comment=order.address.comment,
        ),
        payment_method=PaymentMethodResponse(
            id=order.payment_method.id,
            created_at=order.payment_method.created_at,
            type=order.payment_method.brand,
            card_last4=order.payment_method.last4,
            card_brand=order.payment_method.brand,
            is_default=order.payment_method.is_default,
        ),
        comment=order.comment,
        cancel_reason=order.cancel_reason,
        created_at=order.created_at,
        paid_at=order.created_at,
        delivered_at=None,
    )