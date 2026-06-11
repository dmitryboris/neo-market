from uuid import UUID
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.models import Cart
from src.models.cart_item import CartItem as CartItemModel
from src.services.b2b_client import get_sku, batch_get_products
from src.schemas.cart import CartResponse, CartItem, CartValidationIssue, CartValidationResponse
from src.services.exceptions import InsufficientStock
from fastapi import status

async def get_or_create_cart(
    session: AsyncSession,
    user_id: Optional[UUID] = None,
    session_id: Optional[str] = None,
) -> Cart:
    if user_id:
        stmt = select(Cart).where(Cart.user_id == user_id)
        cart = await session.execute(stmt)
        cart = cart.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user_id)
            session.add(cart)
            await session.flush()
        return cart
    elif session_id:
        stmt = select(Cart).where(Cart.session_id == session_id)
        cart = await session.execute(stmt)
        cart = cart.scalar_one_or_none()
        if not cart:
            cart = Cart(session_id=session_id)
            session.add(cart)
            await session.flush()
        return cart
    raise ValueError("Either user_id or session_id must be provided")

async def add_cart_item_service(
    session: AsyncSession,
    cart: Cart,
    sku_id: UUID,
    quantity: int,
) -> tuple[CartResponse, int]:
    sku_info = await get_sku(sku_id)
    if sku_info["active_quantity"] < quantity:
        raise InsufficientStock(f"Insufficient stock for SKU {sku_id}")

    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id, CartItemModel.sku_id == sku_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    status_code = status.HTTP_201_CREATED if item is None else status.HTTP_200_OK
    if item:
        item.quantity += quantity
        item.product_id = sku_info["product_id"]
    else:
        item = CartItemModel(
            cart_id=cart.id,
            sku_id=sku_id,
            product_id=sku_info["product_id"],
            quantity=quantity,
        )
        session.add(item)
    await session.flush()
    enriched = await enrich_cart(session, cart)
    return enriched, status_code

async def update_cart_item_quantity(
    session: AsyncSession,
    cart: Cart,
    sku_id: UUID,
    new_quantity: int
) -> CartItemModel:
    if new_quantity <= 0:
        raise ValueError("Quantity must be positive")
    await get_sku(sku_id, new_quantity)
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id, CartItemModel.sku_id == sku_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise ValueError("Item not found in cart")
    item.quantity = new_quantity
    await session.flush()
    return item

async def remove_cart_item(
    session: AsyncSession,
    cart: Cart,
    sku_id: UUID
) -> None:
    stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart.id, CartItemModel.sku_id == sku_id)
    await session.execute(stmt)
    await session.flush()

async def clear_cart_service(
    session: AsyncSession,
    cart: Cart
) -> None:
    stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
    await session.execute(stmt)
    await session.flush()

async def enrich_cart(session: AsyncSession, cart: Cart) -> CartResponse:
    stmt = select(CartItemModel).where(CartItemModel.cart_id == cart.id)
    result = await session.execute(stmt)
    items = result.scalars().all()
    if not items:
        return CartResponse(
            id=cart.id,
            items=[],
            items_count=0,
            subtotal=0,
            is_valid=True,
            updated_at=cart.updated_at,
        )

    product_ids = list({item.product_id for item in items if item.product_id})
    if not product_ids:
        cart_items = []
        for item in items:
            cart_items.append(CartItem(
                sku_id=item.sku_id,
                product_id=item.product_id or UUID(int=0),
                name="Товар недоступен",
                quantity=item.quantity,
                unit_price=0,
                line_total=0,
                available_quantity=0,
                is_available=False,
            ))
        return CartResponse(
            id=cart.id,
            items=cart_items,
            items_count=sum(i.quantity for i in items),
            subtotal=0,
            is_valid=False,
            updated_at=cart.updated_at,
        )

    products_data = await batch_get_products(product_ids)

    sku_data: Dict[UUID, dict] = {}
    for prod_id, prod_info in products_data.items():
        for sku_id, sku_info in prod_info["skus"].items():
            sku_data[sku_id] = {
                **sku_info,
                "product_id": prod_id,
                "product_status": prod_info["status"],
                "product_title": prod_info["title"],
            }

    cart_items = []
    subtotal = 0
    is_valid = True
    for item in items:
        data = sku_data.get(item.sku_id)
        if not data:
            cart_items.append(CartItem(
                sku_id=item.sku_id,
                product_id=item.product_id or UUID(int=0),
                name="Товар недоступен",
                quantity=item.quantity,
                unit_price=0,
                line_total=0,
                available_quantity=0,
                is_available=False,
            ))
            is_valid = False
            continue

        unit_price = data["price"]
        available_qty = data["active_quantity"]
        product_status = data["product_status"]
        if product_status != "MODERATED":
            is_available = False
        else:
            is_available = (available_qty >= item.quantity)
        if not is_available:
            is_valid = False
        line_total = unit_price * item.quantity if is_available else 0
        if is_available:
            subtotal += line_total

        cart_items.append(CartItem(
            sku_id=item.sku_id,
            product_id=data["product_id"],
            name=data.get("name") or data["product_title"],
            sku_code=data.get("sku_code"),
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=line_total,
            available_quantity=available_qty,
            is_available=is_available,
            image=None,
        ))

    items_count = sum(i.quantity for i in items)
    return CartResponse(
        id=cart.id,
        items=cart_items,
        items_count=items_count,
        subtotal=subtotal,
        is_valid=is_valid,
        updated_at=cart.updated_at,
    )

async def validate_cart_service(
    session: AsyncSession,
    cart: Cart
) -> CartValidationResponse:
    enriched = await enrich_cart(session, cart)
    issues = []
    for item in enriched.items:
        if not item.is_available:
            reason = "OUT_OF_STOCK" if item.available_quantity == 0 else "PRODUCT_BLOCKED"
            issues.append(CartValidationIssue(
                sku_id=item.sku_id,
                type=reason,
                message=f"Товар {item.name} недоступен",
            ))
    is_valid = len(issues) == 0
    return CartValidationResponse(is_valid=is_valid, cart=enriched, issues=issues)

async def merge_carts_service(
    session: AsyncSession,
    user_id: UUID,
    session_id: str
) -> Cart:
    user_cart = await get_or_create_cart(session, user_id=user_id)
    guest_cart = await get_or_create_cart(session, session_id=session_id)
    if guest_cart.id == user_cart.id:
        return user_cart
    stmt = select(CartItemModel).where(CartItemModel.cart_id == guest_cart.id)
    result = await session.execute(stmt)
    guest_items = result.scalars().all()
    for guest_item in guest_items:
        stmt2 = select(CartItemModel).where(CartItemModel.cart_id == user_cart.id, CartItemModel.sku_id == guest_item.sku_id)
        res2 = await session.execute(stmt2)
        existing = res2.scalar_one_or_none()
        if existing:
            existing.quantity = max(existing.quantity, guest_item.quantity)
        else:
            new_item = CartItemModel(
                cart_id=user_cart.id,
                sku_id=guest_item.sku_id,
                product_id=guest_item.product_id,
                quantity=guest_item.quantity,
            )
            session.add(new_item)
    await session.execute(delete(CartItemModel).where(CartItemModel.cart_id == guest_cart.id))
    await session.execute(delete(Cart).where(Cart.id == guest_cart.id))
    await session.flush()
    return user_cart