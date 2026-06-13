from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    ASSEMBLING = "ASSEMBLING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    CANCEL_PENDING = "CANCEL_PENDING"


class PaymentMethodType(str, Enum):
    CARD = "CARD"
    SBP = "SBP"
    WALLET = "WALLET"


class CardBrand(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    MIR = "MIR"


class NotificationType(str, Enum):
    ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED"
    BACK_IN_STOCK = "BACK_IN_STOCK"
    PRICE_DROP = "PRICE_DROP"
    PROMO = "PROMO"
    SYSTEM = "SYSTEM"


class AddressCreateRequest(BaseModel):
    country: str = Field(max_length=100)
    region: Optional[str] = Field(None, max_length=200)
    city: str = Field(max_length=200)
    street: str = Field(max_length=200)
    building: str = Field(max_length=50)
    apartment: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    recipient_name: Optional[str] = Field(None, max_length=200)
    recipient_phone: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    is_default: bool = False
    comment: Optional[str] = Field(None, max_length=500)


class AddressResponse(AddressCreateRequest):
    id: UUID
    created_at: datetime


class PaymentMethodCreateRequest(BaseModel):
    type: PaymentMethodType
    card_last4: Optional[str] = Field(None, pattern=r'^[0-9]{4}$')
    card_brand: Optional[CardBrand] = None
    is_default: bool = False


class PaymentMethodResponse(PaymentMethodCreateRequest):
    id: UUID
    created_at: datetime


class ImageRef(BaseModel):
    id: UUID
    url: HttpUrl
    alt: Optional[str] = None
    ordering: int = Field(ge=0)
    is_main: bool


class OrderItem(BaseModel):
    sku_id: UUID
    product_id: UUID
    name: str
    sku_code: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: int = Field(description="Цена за единицу, зафиксированная при создании заказа")
    line_total: int
    image_url: Optional[HttpUrl] = None


class StatusHistoryEntry(BaseModel):
    status: OrderStatus
    changed_at: datetime
    reason: Optional[str] = None


class OrderResponse(BaseModel):
    id: UUID
    number: Optional[str] = Field(None, description="Человекочитаемый номер заказа")
    buyer_id: UUID
    status: OrderStatus
    status_history: List[StatusHistoryEntry] = Field(default_factory=list)
    items: List[OrderItem]
    subtotal: int = Field(description="Сумма по позициям, копейки")
    delivery_cost: int = 0
    total: int = Field(description="subtotal + delivery_cost")
    address: AddressResponse
    payment_method: PaymentMethodResponse
    comment: Optional[str] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class OrderCreateRequestItem(BaseModel):
    """Элемент для опционального снапшота корзины"""
    sku_id: UUID
    quantity: int = Field(ge=1)
    unit_price: int = Field(ge=0)


class OrderCreateRequest(BaseModel):
    address_id: UUID
    payment_method_id: UUID
    comment: Optional[str] = Field(None, max_length=1000)
    items_snapshot: Optional[List[OrderCreateRequestItem]] = Field(
        None,
        description="Опционально: явный снапшот корзины для защиты от гонок"
    )