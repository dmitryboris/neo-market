from pydantic import BaseModel
from typing import List
 
class InvoiceItemCreate(BaseModel):
    sku_id: int
    quantity: int
    price: int  # закупочная цена
 
class InvoiceCreate(BaseModel):
    items: List[InvoiceItemCreate]
 
class InvoiceAccept(BaseModel):
    invoice_id: int