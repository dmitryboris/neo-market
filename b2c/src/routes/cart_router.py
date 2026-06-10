from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user, get_session_id, get_current_user_optional
from src.services import cart_service
from src.models import Buyer
from src.schemas.cart import CartItemAddRequest, CartItemUpdateRequest, CartResponse, CartValidationResponse
import uuid

cart_router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])

async def _get_cart_and_db(
    current_user: Buyer | None = Depends(get_current_user_optional),
    session_id: str | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_session),
):
    # Если есть JWT – используем user_id (даже если есть session_id, он игнорируется)
    if current_user:
        cart = await cart_service.get_or_create_cart(db, user_id=current_user.id)
    elif session_id:
        cart = await cart_service.get_or_create_cart(db, session_id=session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "Either authentication or X-Session-Id required"}
        )
    return db, cart

@cart_router.get("", response_model=CartResponse)
async def get_cart(
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    return await cart_service.enrich_cart(db, cart)

@cart_router.post("/items", status_code=200, response_model=CartResponse)
async def add_cart_item(
    item: CartItemAddRequest,
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    try:
        await cart_service.add_cart_item(db, cart, item.sku_id, item.quantity)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INSUFFICIENT_STOCK", "message": str(e)}
        )
    return await cart_service.enrich_cart(db, cart)

@cart_router.patch("/items/{sku_id}", response_model=CartResponse)
async def update_cart_item(
    sku_id: uuid.UUID,
    update: CartItemUpdateRequest,
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    try:
        await cart_service.update_cart_item_quantity(db, cart, sku_id, update.quantity)
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(e)}
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INSUFFICIENT_STOCK", "message": str(e)}
        )
    return await cart_service.enrich_cart(db, cart)

@cart_router.delete("/items/{sku_id}", response_model=CartResponse)
async def delete_cart_item(
    sku_id: uuid.UUID,
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    await cart_service.remove_cart_item(db, cart, sku_id)
    await db.commit()
    return await cart_service.enrich_cart(db, cart)

@cart_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    await cart_service.clear_cart(db, cart)
    await db.commit()
    return None

@cart_router.post("/validate", response_model=CartValidationResponse)
async def validate_cart(
    db_cart = Depends(_get_cart_and_db)
):
    db, cart = db_cart
    return await cart_service.validate_cart(db, cart)

@cart_router.post("/merge", response_model=CartResponse)
async def merge_carts(
    session_id: str = Depends(get_session_id),
    current_user: Buyer = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not current_user or not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "Requires both JWT and X-Session-Id"}
        )
    cart = await cart_service.merge_carts(db, current_user.id, session_id)
    await db.commit()
    return await cart_service.enrich_cart(db, cart)