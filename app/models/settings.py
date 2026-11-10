from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.base import BaseMongoModel


class TaxRate(BaseModel):
    name: str  # e.g., "VAT", "Sales Tax"
    rate_percent: float = Field(ge=0, le=100)
    country: str = "US"
    is_active: bool = True


class ShippingMethod(BaseModel):
    id: str
    name: str  # e.g., "Standard Ground", "Express 2-Day"
    price: float = Field(ge=0)
    estimated_days: str = "3-5 business days"
    free_shipping_threshold: Optional[float] = Field(default=None, ge=0)
    is_active: bool = True


class StoreSettings(BaseMongoModel):
    key: str = "global_store_settings"
    store_name: str = "Apex Commerce"
    store_url: Optional[str] = "https://apexcommerce.io"
    support_email: EmailStr = "support@apexcommerce.io"
    support_phone: Optional[str] = "+1 (800) 555-0199"
    currency_code: str = "USD"
    currency_symbol: str = "$"
    timezone: str = "UTC"
    tax_rates: List[TaxRate] = Field(default_factory=lambda: [
        TaxRate(name="Standard State Tax", rate_percent=7.5, country="US")
    ])
    shipping_methods: List[ShippingMethod] = Field(default_factory=lambda: [
        ShippingMethod(id="std", name="Standard Shipping", price=5.99, estimated_days="3-5 days", free_shipping_threshold=50.0),
        ShippingMethod(id="exp", name="Express Courier", price=14.99, estimated_days="1-2 days")
    ])
    maintenance_mode: bool = False
    order_number_prefix: str = "ORD"
    low_stock_alert_threshold: int = 5
