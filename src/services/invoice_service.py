from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from src.models.sku import SKU
from src.schemas.invoice import InvoiceCreate
 
async def create_invoice(db: AsyncSession, seller_id: int, data: InvoiceCreate) -> Invoice:
    invoice = Invoice(seller_id=seller_id)
    db.add(invoice)
    await db.flush()
    for item_data in data.items:
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            sku_id=item_data.sku_id,
            quantity=item_data.quantity,
            price=item_data.price
        ))
    await db.commit()
    await db.refresh(invoice)
    return invoice
 
async def accept_invoice(db: AsyncSession, invoice_id: int) -> Invoice | None:
    invoice = await db.get(Invoice, invoice_id, options=[selectinload(Invoice.items)])
    if not invoice or invoice.status != InvoiceStatus.DRAFT:
        return None
 
    # обновляем остатки SKU
    for item in invoice.items:
        sku = await db.get(SKU, item.sku_id)
        if sku:
            sku.active_quantity += item.quantity
    invoice.status = InvoiceStatus.ACCEPTED
    invoice.accepted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invoice)
    return invoice