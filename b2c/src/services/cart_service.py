import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.models import Cart, CartItem
from src.services.b2b_client import batch_get_skus, check_sku
from src.schemas.cart import CartResponse, CartItemResponse, CartValidationIssue, CartValidationResponse
from datetime import datetime

async def get_or_create_cart(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    session_id: Optional[str] = None
) -> Cart:
    if not user_id and not session_id:
        raise ValueError("Either user_id or session_id must be provided")
    if user_id:
        stmt = select(Cart).where(Cart.user_id == user_id)
        cart = await db.execute(stmt)
        cart = cart.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            await db.flush()
        return cart
    else:
        stmt = select(Cart).where(Cart.session_id == session_id)
        cart = await db.execute(stmt)
        cart = cart.scalar_one_or_none()
        if not cart:
            cart = Cart(session_id=session_id)
            db.add(cart)
            await db.flush()
        return cart

async def add_cart_item(
    db: AsyncSession,
    cart: Cart,
    sku_id: uuid.UUID,
    quantity: int
) -> CartItem:
    sku_info = await check_sku(sku_id, quantity)  # из b2b_client
    stmt = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == sku_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(
            cart_id=cart.id,
            sku_id=sku_id,
            product_id=sku_info["product_id"],
            quantity=quantity,
        )
        db.add(item)
    await db.flush()
    return item

async def update_cart_item_quantity(
    db: AsyncSession,
    cart: Cart,
    sku_id: uuid.UUID,
    new_quantity: int
) -> CartItem:
    if new_quantity <= 0:
        raise ValueError("Quantity must be positive")
    await check_sku(sku_id, new_quantity)
    stmt = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == sku_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise ValueError("Item not found in cart")
    item.quantity = new_quantity
    await db.flush()
    return item

async def remove_cart_item(
    db: AsyncSession,
    cart: Cart,
    sku_id: uuid.UUID
) -> None:
    stmt = delete(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == sku_id)
    await db.execute(stmt)
    await db.flush()

async def clear_cart(
    db: AsyncSession,
    cart: Cart
) -> None:
    stmt = delete(CartItem).where(CartItem.cart_id == cart.id)
    await db.execute(stmt)
    await db.flush()

async def enrich_cart(
    db: AsyncSession,
    cart: Cart
) -> CartResponse:
    stmt = select(CartItem).where(CartItem.cart_id == cart.id)
    result = await db.execute(stmt)
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
    sku_ids = [item.sku_id for item in items]
    b2b_data = await batch_get_skus(sku_ids)   # из b2b_client
    cart_items = []
    subtotal = 0
    is_valid = True
    for item in items:
        data = b2b_data.get(str(item.sku_id))
        if not data:
            cart_items.append(CartItemResponse(
                sku_id=item.sku_id,
                product_id=item.product_id or uuid.UUID(int=0),
                name="Товар недоступен",
                quantity=item.quantity,
                unit_price=0,
                line_total=0,
                available_quantity=0,
                is_available=False,
            ))
            is_valid = False
            continue
        unit_price = data.get("price", 0)
        line_total = unit_price * item.quantity
        available_qty = data.get("active_quantity", 0)
        is_available = (available_qty >= item.quantity) and data.get("is_visible", False)
        if not is_available:
            is_valid = False
        cart_items.append(CartItemResponse(
            sku_id=item.sku_id,
            product_id=data["product_id"],
            name=data["name"],
            sku_code=data.get("sku_code"),
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=line_total,
            available_quantity=available_qty,
            is_available=is_available,
            image=None,
        ))
        subtotal += line_total
    items_count = sum(i.quantity for i in items)
    return CartResponse(
        id=cart.id,
        items=cart_items,
        items_count=items_count,
        subtotal=subtotal,
        is_valid=is_valid,
        updated_at=cart.updated_at,
    )

async def validate_cart(
    db: AsyncSession,
    cart: Cart
) -> CartValidationResponse:
    enriched = await enrich_cart(db, cart)
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

async def merge_carts(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: str
) -> Cart:
    user_cart = await get_or_create_cart(db, user_id=user_id)
    guest_cart = await get_or_create_cart(db, session_id=session_id)
    if guest_cart.id == user_cart.id:
        return user_cart
    # Перенести элементы
    stmt = select(CartItem).where(CartItem.cart_id == guest_cart.id)
    result = await db.execute(stmt)
    guest_items = result.scalars().all()
    for guest_item in guest_items:
        stmt2 = select(CartItem).where(CartItem.cart_id == user_cart.id, CartItem.sku_id == guest_item.sku_id)
        res2 = await db.execute(stmt2)
        existing = res2.scalar_one_or_none()
        if existing:
            existing.quantity = max(existing.quantity, guest_item.quantity)
        else:
            new_item = CartItem(
                cart_id=user_cart.id,
                sku_id=guest_item.sku_id,
                product_id=guest_item.product_id,
                quantity=guest_item.quantity,
            )
            db.add(new_item)
    # Удалить гостевую корзину
    await db.execute(delete(CartItem).where(CartItem.cart_id == guest_cart.id))
    await db.execute(delete(Cart).where(Cart.id == guest_cart.id))
    await db.flush()
    return user_cart