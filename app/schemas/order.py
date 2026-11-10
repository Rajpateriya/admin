from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.customer import Address
from app.models.order import OrderItem, OrderNote, OrderStatus, PaymentStatus, ShippingInfo


class OrderItemCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: Optional[float] = Field(default=None, ge=0)


class OrderCreateRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_email: EmailStr
    customer_name: str = Field(min_length=1)
    items: List[OrderItemCreate] = Field(min_length=1)
    shipping_address: Address
    billing_address: Optional[Address] = None
    coupon_code: Optional[str] = None
    shipping_amount: float = Field(default=0.0, ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    payment_method: Optional[str] = "MANUAL_ADMIN"
    notes: Optional[str] = None


class OrderCancelRequest(BaseModel):
    reason: str = Field(min_length=3)
    restock_inventory: bool = True


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None


class OrderTrackingUpdateRequest(BaseModel):
    carrier: str
    tracking_number: str
    tracking_url: Optional[str] = None


class OrderRefundRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount to refund")
    reason: str = Field(min_length=3)
    restock_inventory: bool = True


class OrderNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1)


class OrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    customer_email: str
    customer_name: str
    items: List[OrderItem]
    shipping_address: Address
    billing_address: Address
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: Optional[str] = None
    subtotal: float
    discount_amount: float
    tax_amount: float
    shipping_amount: float
    total_amount: float
    coupon_code: Optional[str] = None
    shipping_info: Optional[ShippingInfo] = None
    admin_notes: List[OrderNote] = Field(default_factory=list)
    cancellation_reason: Optional[str] = None
    refunded_amount: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
