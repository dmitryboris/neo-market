from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user, get_session_id, get_current_user_optional
from src.services.cart_service import (get_or_create_cart, enrich_cart, add_cart_item_service, update_cart_item_quantity, remove_cart_item,
                                    clear_cart_service, validate_cart_service, merge_carts_service)
from src.models import Buyer
from src.schemas.cart import CartItemAddRequest, CartItemUpdateRequest, CartResponse, CartValidationResponse
from uuid import UUID
from src.services.exceptions import InvalidAuth

cart_router = APIRouter(prefix="/cart", tags=["Cart"])

async def _get_cart_and_session(
    current_user: Buyer | None = Depends(get_current_user_optional),
    session_id: str | None = Depends(get_session_id),
    session: AsyncSession = Depends(get_session),
):
    if current_user:
        cart = await get_or_create_cart(session, user_id=current_user.id)
    elif session_id:
        cart = await get_or_create_cart(session, session_id=session_id)
    else:
        raise InvalidAuth()
    return session, cart

@cart_router.get("", response_model=CartResponse)
async def get_cart(
    session_cart = Depends(_get_cart_and_session)
):
    session, cart = session_cart
    return await enrich_cart(session, cart)

@cart_router.post("/items", response_model=CartResponse)
async def add_cart_item(
    item: CartItemAddRequest,
    session_cart = Depends(_get_cart_and_session),
    response: Response = None
):
    session, cart = session_cart
    enriched_cart, status_code = await add_cart_item_service(session, cart, item.sku_id, item.quantity)
    await session.commit()
    response.status_code = status_code
    return enriched_cart

@cart_router.patch("/items/{sku_id}", status_code=status.HTTP_200_OK, response_model=CartResponse)
async def update_cart_item(
    sku_id: UUID,
    update: CartItemUpdateRequest,
    session_cart = Depends(_get_cart_and_session)
):
    session, cart = session_cart
    enriched_cart = await update_cart_item_quantity(session, cart, sku_id, update.quantity)
    await session.commit()
    return enriched_cart

@cart_router.delete("/items/{sku_id}", response_model=CartResponse)
async def delete_cart_item(
    sku_id: UUID,
    session_cart = Depends(_get_cart_and_session)
):
    session, cart = session_cart
    await remove_cart_item(session, cart, sku_id)
    await session.commit()
    return await enrich_cart(session, cart)

@cart_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    session_cart = Depends(_get_cart_and_session)
):
    session, cart = session_cart
    await clear_cart_service(session, cart)
    await session.commit()
    return None

@cart_router.post("/validate", response_model=CartValidationResponse)
async def validate_cart(
    session_cart = Depends(_get_cart_and_session)
):
    session, cart = session_cart
    return await validate_cart_service(session, cart)

@cart_router.post("/merge", response_model=CartResponse)
async def merge_carts(
    session_id: str = Depends(get_session_id),
    current_user: Buyer = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not current_user or not session_id:
        raise InvalidAuth("Requires both JWT and X-Session-Id")
    
    cart = await merge_carts_service(session, current_user.id, session_id)
    await session.commit()
    return await enrich_cart(session, cart)