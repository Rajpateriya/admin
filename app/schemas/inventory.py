from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.inventory import StockAdjustmentReason


class StockAdjustmentCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity_delta: int = Field(description="Negative to deduct, positive to add stock")
    reason: StockAdjustmentReason
    reference_id: Optional[str] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: str
    product_id: str
    variant_id: Optional[str] = None
    product_title: Optional[str] = None
    quantity_delta: int
    previous_stock: int
    new_stock: int
    reason: StockAdjustmentReason
    reference_id: Optional[str] = None
    performed_by_id: str
    performed_by_email: str
    notes: Optional[str] = None
    created_at: datetime


class LowStockAlertResponse(BaseModel):
    product_id: str
    title: str
    sku: str
    stock_quantity: int
    low_stock_threshold: int
    variant_id: Optional[str] = None
    variant_title: Optional[str] = None
