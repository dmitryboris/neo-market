from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.dependencies import get_current_user
from models.seller import Seller
from schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceListResponse
from services import invoice_service
from services import exceptions as exc

invoice_router = APIRouter(prefix="/invoices", tags=["Invoices"])


@invoice_router.get("", response_model=InvoiceListResponse, summary="List invoices")
async def get_invoices(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    return await invoice_service.get_invoices(session, current_seller.id, limit, offset)


@invoice_router.get("/{invoice_id}", response_model=InvoiceResponse, summary="Get invoice")
async def get_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    try:
        return await invoice_service.get_invoice_by_id(session, invoice_id, seller_id=current_seller.id)
    except exc.InvoiceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    except exc.InvoiceAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this invoice")


@invoice_router.post(
    "", response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invoice"
)
async def create_invoice(
    request: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user)
):
    try:
        return await invoice_service.create_invoice(session, current_seller, request)
    except exc.DuplicateSKUInInvoice as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except exc.SKUNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except exc.SKUNotBelongsToSeller as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@invoice_router.post(
    "/{invoice_id}/accept",
    response_model=InvoiceResponse,
    summary="Accept invoice – increase SKU stock"
)
async def accept_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user),
):
    try:
        return await invoice_service.accept_invoice(session, invoice_id, current_seller)
    except exc.InvoiceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    except exc.InvoiceAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except exc.InvoiceAlreadyAccepted as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except exc.SKUNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
@invoice_router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete invoice (only CREATED status)"
)
async def delete_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_seller: Seller = Depends(get_current_user),
):
    try:
        await invoice_service.delete_invoice(session, invoice_id, current_seller)
    except exc.InvoiceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    except exc.InvoiceAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except exc.InvoiceCannotDeleteAccepted as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))