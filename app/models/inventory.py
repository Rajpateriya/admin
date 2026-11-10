from enum import Enum
from typing import Optional
from app.models.base import BaseMongoModel


class StockAdjustmentReason(str, Enum):
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    MANUAL_CORRECTION = "MANUAL_CORRECTION"
    DAMAGED = "DAMAGED"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    ORDER_FULFILLMENT = "ORDER_FULFILLMENT"
    INVENTORY_AUDIT = "INVENTORY_AUDIT"


class StockMovement(BaseMongoModel):
    product_id: str
    variant_id: Optional[str] = None
    product_title: Optional[str] = None
    quantity_delta: int  # Positive for addition, negative for reduction
    previous_stock: int
    new_stock: int
    reason: StockAdjustmentReason
    reference_id: Optional[str] = None
    performed_by_id: str
    performed_by_email: str
    notes: Optional[str] = None
