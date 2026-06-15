from uuid import UUID
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Order, OrderItem as OrderItemModel, Address, PaymentMethod, IdempotencyRecord
from src.models.order import OrderStatus
from src.schemas.order import OrderResponse, OrderItem as OrderItemSchema, AddressResponse, PaymentMethodResponse
from src.services.cart_service import enrich_cart, get_or_create_cart
from src.services.b2b_client import reserve_skus, unreserve_skus
from src.services.exceptions import (
    CartInvalidException, CartMismatchException, ReserveFailed, AddressNotFound, PaymentMethodNotFound, IdempotencyConflict,
    OrderNotFound, CancelNotAllowed, B2BUnavailable
)
import hashlib
import json

async def create_order(
    session: AsyncSession,
    buyer_id: UUID,
    idempotency_key: UUID,
    address_id: UUID,
    payment_method_id: UUID,
    comment: Optional[str] = None,
    items_snapshot: Optional[List[dict]] = None,
) -> OrderResponse:
    request_hash = _hash_request(address_id, payment_method_id, comment, items_snapshot)

    existing_record = await session.get(IdempotencyRecord, idempotency_key)

    if existing_record:
        if existing_record.request_hash != request_hash:
            raise IdempotencyConflict()

        order = await session.get(Order, existing_record.order_id)
        if not order:
            await session.delete(existing_record)
            await session.commit()
        else:
            address, payment_method, items = await _load_order_context(session, order)
            return _order_to_response(order, address, payment_method, items)

    cart = await get_or_create_cart(session, user_id=buyer_id)
    enriched_cart = await enrich_cart(session, cart)

    if not enriched_cart.items:
        raise CartInvalidException({
            "is_valid": False,
            "cart": enriched_cart.model_dump(mode="json"),
            "issues": [
                {
                    "sku_id": None,
                    "type": "EMPTY_CART",
                    "message": "Cart is empty"
                }
            ]
        })

    failed_items = []
    for item in enriched_cart.items:
        if not item.is_available:
            reason = "OUT_OF_STOCK" if item.available_quantity == 0 else "PRODUCT_BLOCKED"
            failed_items.append({
                "sku_id": str(item.sku_id),
                "requested": item.quantity,
                "available": item.available_quantity,
                "reason": reason,
            })
        elif item.quantity > item.available_quantity:
                failed_items.append({
                "sku_id": str(item.sku_id),
                "requested": item.quantity,
                "available": item.available_quantity,
                "reason": "INSUFFICIENT_STOCK",
            })

    if failed_items:
        raise ReserveFailed(failed_items)

    if items_snapshot is not None:
        snapshot_map = {str(i["sku_id"]): i for i in items_snapshot}
        for item in enriched_cart.items:
            snap = snapshot_map.get(str(item.sku_id))
            if not snap or snap["quantity"] != item.quantity or snap["unit_price"] != item.unit_price:
                raise CartMismatchException()

    address = await session.get(Address, address_id)
    if not address or address.buyer_id != buyer_id:
        raise AddressNotFound()

    payment_method = await session.get(PaymentMethod, payment_method_id)
    if not payment_method or payment_method.buyer_id != buyer_id:
        raise PaymentMethodNotFound()
    
    order = Order(
        user_id=buyer_id,
        status=OrderStatus.PAID,
        total_amount=0,
        address_id=address_id,
        payment_method_id=payment_method_id,
        comment=comment,
    )

    session.add(order)
    await session.flush()

    reserve_items = [
        {"sku_id": str(item.sku_id), "quantity": item.quantity}
        for item in enriched_cart.items
    ]
    reserve_result = await reserve_skus(
        idempotency_key=idempotency_key,
        order_id=order.id,
        items=reserve_items,
    )

    if not reserve_result.get("reserved", False):
        raise ReserveFailed(reserve_result.get("failed_items", []))


    if not existing_record:
        session.add(
            IdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                order_id=order.id,
            )
        )

    total_amount = 0

    for item in enriched_cart.items:
        line_total = item.unit_price * item.quantity
        total_amount += line_total

        session.add(OrderItemModel(
            order_id=order.id,
            sku_id=item.sku_id,
            product_id=item.product_id,
            product_title=getattr(item, 'product_title', item.name),
            sku_name=getattr(item, 'sku_name', item.name),
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=line_total,
        ))

    order.total_amount = total_amount

    await session.commit()

    address, payment_method, items = await _load_order_context(session, order)
    return _order_to_response(order, address, payment_method, items)


async def cancel_order(
    session: AsyncSession,
    order_id: UUID,
    buyer_id: UUID,
) -> OrderResponse:
    order = await session.get(Order, order_id)

    if not order or order.user_id != buyer_id:
        raise OrderNotFound()
    allowed_statuses = {
        OrderStatus.CREATED,
        OrderStatus.PAID,
        OrderStatus.ASSEMBLING,
        OrderStatus.DELIVERING,
    }

    if order.status not in allowed_statuses:
        raise CancelNotAllowed(order.status)
    items_query = await session.execute(
        select(OrderItemModel).where(
            OrderItemModel.order_id == order.id
        )
    )

    items = items_query.scalars().all()
    order.status = OrderStatus.CANCEL_PENDING
    await session.flush()
    await session.commit()

    try:
        await unreserve_skus(
            order.id,
            [
                {
                    "sku_id": str(item.sku_id),
                    "quantity": item.quantity,
                }
                for item in items
            ],
        )
        order.status = OrderStatus.CANCELLED
    except B2BUnavailable:
        order.status = OrderStatus.CANCEL_PENDING

    await session.commit()

    address, payment_method, items = await _load_order_context(
        session,
        order,
    )

    return _order_to_response(
        order,
        address,
        payment_method,
        items,
    )

def _order_to_response(order: Order, address: Address, payment_method: PaymentMethod, items: List[OrderItemModel]) -> OrderResponse:
    order_items = []
    for item in items:
        order_items.append(OrderItemSchema(
            sku_id=item.sku_id,
            product_id=item.product_id,
            name=f"{item.product_title} {item.sku_name}".strip(),
            sku_code=None,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            image_url=None,
        ))

    subtotal = sum(i.line_total for i in items)

    address_response = AddressResponse(
        id=address.id,
        created_at=address.created_at,
        country=address.country,
        region=address.region,
        city=address.city,
        street=address.street,
        building=address.building,
        apartment=address.apartment,
        postal_code=address.postal_code,
        recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone,
        is_default=address.is_default,
        comment=address.comment,
    )

    payment_method_response = PaymentMethodResponse(
        id=payment_method.id,
        created_at=payment_method.created_at,
        type=payment_method.type,
        card_last4=payment_method.last4,
        card_brand=payment_method.brand,
        is_default=payment_method.is_default,
    )

    return OrderResponse(
        id=order.id,
        number=None,
        buyer_id=order.user_id,
        status=order.status,
        status_history=[],
        items=order_items,
        subtotal=subtotal,
        delivery_cost=0,
        total=order.total_amount,
        address=address_response,
        payment_method=payment_method_response,
        comment=order.comment,
        cancel_reason=order.cancel_reason,
        created_at=order.created_at,
        paid_at=order.created_at,
        delivered_at=None,
    )

def _hash_request(address_id: UUID, payment_method_id: UUID, comment: str | None, items_snapshot: list | None) -> str:

    data = {
        "address_id": str(address_id),
        "payment_method_id": str(payment_method_id),
        "comment": comment,
        "items_snapshot": items_snapshot,
    }
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


async def _load_order_context(session: AsyncSession, order: Order):
    address = await session.get(Address, order.address_id)
    if not address:
        raise AddressNotFound()

    payment_method = await session.get(PaymentMethod, order.payment_method_id)
    if not payment_method:
        raise PaymentMethodNotFound()

    items_query = await session.execute(
        select(OrderItemModel).where(OrderItemModel.order_id == order.id)
    )
    items = items_query.scalars().all()

    return address, payment_method, items