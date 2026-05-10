from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from src.models.invoice import Invoice, InvoiceStatus
from src.models.invoice_item import InvoiceItem
from src.models.sku import SKU
from src.models.product import Product
from src.models.seller import Seller
from src.schemas.invoice import InvoiceCreate
from src.services import exceptions as exc


async def get_invoice_by_id(session: AsyncSession, invoice_id, seller_id=None) -> Invoice:
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.items).selectinload(InvoiceItem.sku))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise exc.InvoiceNotFound("Invoice not found")
    if seller_id is not None and invoice.seller_id != seller_id:
        raise exc.InvoiceAccessDenied("Access denied to this invoice")

    return invoice


async def get_invoices(session: AsyncSession, seller_id, limit: int = 20, offset: int = 0) -> dict:
    total_result = await session.execute(
        select(func.count(Invoice.id)).where(Invoice.seller_id == seller_id)
    )
    total = total_result.scalar_one()
    result = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.seller_id == seller_id)
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return {
        "total": total,
        "items": result.scalars().all(),
    }


async def create_invoice(session: AsyncSession, seller: Seller, request: InvoiceCreate) -> Invoice:
    sku_ids = [item.sku_id for item in request.items]
    if len(sku_ids) != len(set(sku_ids)):
        raise exc.DuplicateSKUInInvoice("Duplicate SKU IDs in invoice items")

    result = await session.execute(
        select(SKU)
        .options(selectinload(SKU.product))
        .where(SKU.id.in_(sku_ids))
    )
    skus = result.scalars().all()
    skus_dict = {sku.id: sku for sku in skus}

    for item in request.items:
        sku = skus_dict.get(item.sku_id)
        if not sku:
            raise exc.SKUNotFound(f"SKU {item.sku_id} not found")
        if sku.product.seller_id != seller.id:
            raise exc.SKUNotBelongsToSeller(f"SKU {item.sku_id} does not belong to your products")

    invoice = Invoice(seller_id=seller.id, status=InvoiceStatus.CREATED)
    session.add(invoice)
    await session.flush()

    for item in request.items:
        session.add(InvoiceItem(
            invoice_id=invoice.id,
            sku_id=item.sku_id,
            quantity=item.quantity,
        ))

    await session.commit()
    return await get_invoice_by_id(session, invoice.id)


async def accept_invoice(session: AsyncSession, invoice_id, seller: Seller) -> Invoice:
    invoice = await get_invoice_by_id(session, invoice_id, seller_id=seller.id)
    if invoice.status == InvoiceStatus.ACCEPTED:
        raise exc.InvoiceAlreadyAccepted("Invoice already accepted")

    sku_ids = [item.sku_id for item in invoice.items]
    result = await session.execute(
        select(SKU).where(SKU.id.in_(sku_ids)).with_for_update()
    )
    skus = result.scalars().all()
    skus_dict = {sku.id: sku for sku in skus}

    for item in invoice.items:
        sku = skus_dict.get(item.sku_id)
        if not sku:
            raise exc.SKUNotFound(f"SKU {item.sku_id} not found")
        sku.active_quantity += item.quantity

    invoice.status = InvoiceStatus.ACCEPTED
    await session.commit()
    return await get_invoice_by_id(session, invoice.id)


async def delete_invoice(session: AsyncSession, invoice_id, seller: Seller):
    invoice = await get_invoice_by_id(session, invoice_id, seller_id=seller.id)

    if invoice.status == InvoiceStatus.ACCEPTED:
        raise exc.InvoiceCannotDeleteAccepted("Cannot delete accepted invoice")

    await session.delete(invoice)
    await session.commit()