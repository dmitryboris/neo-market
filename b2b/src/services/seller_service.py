from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.seller import Seller
from src.schemas.seller import SellerCreate, SellerUpdate
from shared.security import hash_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_seller_by_id(session: AsyncSession, seller_id) -> Seller | None:
    result = await session.execute(select(Seller).where(Seller.id == seller_id))
    return result.scalar_one_or_none()


async def get_seller_by_email(session: AsyncSession, email: str) -> Seller | None:
    normalized_email = normalize_email(email)
    result = await session.execute(
        select(Seller).where(func.lower(Seller.email) == normalized_email)
    )
    return result.scalar_one_or_none()


async def create_seller(session: AsyncSession, request: SellerCreate) -> Seller:
    seller = Seller(
        email=normalize_email(str(request.email)),
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        middle_name=request.middle_name,
        company_name=request.company_name,
        inn=request.inn,
        phone=str(request.phone) if request.phone else None,
    )
    session.add(seller)
    await session.flush()
    return seller


async def update_seller(session: AsyncSession, seller: Seller, request: SellerUpdate) -> Seller:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(seller, field, value)
    await session.commit()
    await session.refresh(seller)
    return seller


async def delete_seller(session: AsyncSession, seller: Seller) -> None:
    await session.delete(seller)
    await session.commit()
