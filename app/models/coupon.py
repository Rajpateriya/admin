from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field
from app.models.base import BaseMongoModel, utc_now


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"
    FREE_SHIPPING = "FREE_SHIPPING"


class Coupon(BaseMongoModel):
    code: str
    discount_type: DiscountType
    value: float = Field(ge=0, description="Percentage (e.g. 15 for 15%) or Fixed Currency Amount")
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    usage_count: int = Field(default=0, ge=0)
    per_customer_limit: int = Field(default=1, ge=1)
    valid_from: datetime = Field(default_factory=utc_now)
    valid_to: datetime
    is_active: bool = True
    applicable_category_ids: List[str] = Field(default_factory=list)
    applicable_product_ids: List[str] = Field(default_factory=list)
