from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.coupon import DiscountType


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    discount_type: DiscountType
    value: float = Field(ge=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    per_customer_limit: int = Field(default=1, ge=1)
    valid_from: Optional[datetime] = None
    valid_to: datetime
    is_active: bool = True
    applicable_category_ids: List[str] = Field(default_factory=list)
    applicable_product_ids: List[str] = Field(default_factory=list)


class CouponUpdate(BaseModel):
    value: Optional[float] = Field(default=None, ge=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    per_customer_limit: Optional[int] = Field(default=None, ge=1)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: Optional[bool] = None
    applicable_category_ids: Optional[List[str]] = None
    applicable_product_ids: Optional[List[str]] = None


class CouponResponse(BaseModel):
    id: str
    code: str
    discount_type: DiscountType
    value: float
    min_order_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    usage_count: int
    per_customer_limit: int
    valid_from: datetime
    valid_to: datetime
    is_active: bool
    applicable_category_ids: List[str]
    applicable_product_ids: List[str]
    created_at: datetime
    updated_at: datetime


class CartItem(BaseModel):
    product_id: str
    category_id: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=1)
    order_subtotal: float = Field(ge=0)
    customer_id: Optional[str] = None
    items: List[CartItem] = Field(default_factory=list)


class CouponValidateResponse(BaseModel):
    valid: bool
    coupon_code: str
    discount_type: Optional[DiscountType] = None
    discount_amount: float = 0.0
    subtotal: float = 0.0
    final_total: float = 0.0
    message: str


class CouponStatsResponse(BaseModel):
    coupon_id: str
    code: str
    usage_count: int
    usage_limit: Optional[int] = None
    total_discount_given: float = 0.0
    total_orders_revenue: float = 0.0
