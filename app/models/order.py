from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.base import BaseMongoModel, utc_now
from app.models.customer import Address


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    AUTHORIZED = "AUTHORIZED"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class OrderItem(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    title: str
    sku: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    image_url: Optional[str] = None


class ShippingInfo(BaseModel):
    carrier: str
    tracking_number: str
    tracking_url: Optional[str] = None
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None


class OrderNote(BaseModel):
    author_id: str
    author_email: str
    note: str
    created_at: datetime = Field(default_factory=utc_now)


class Order(BaseMongoModel):
    order_number: str
    customer_id: str
    customer_email: str
    customer_name: str
    items: List[OrderItem]
    shipping_address: Address
    billing_address: Address
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    payment_method: Optional[str] = "CREDIT_CARD"
    subtotal: float = Field(ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    shipping_amount: float = Field(default=0.0, ge=0)
    total_amount: float = Field(ge=0)
    coupon_code: Optional[str] = None
    shipping_info: Optional[ShippingInfo] = None
    admin_notes: List[OrderNote] = Field(default_factory=list)
    cancellation_reason: Optional[str] = None
    refunded_amount: float = Field(default=0.0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
