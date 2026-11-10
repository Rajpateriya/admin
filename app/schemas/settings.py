from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.models.settings import ShippingMethod, TaxRate


class StoreSettingsUpdate(BaseModel):
    store_name: Optional[str] = None
    store_url: Optional[str] = None
    support_email: Optional[EmailStr] = None
    support_phone: Optional[str] = None
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    timezone: Optional[str] = None
    tax_rates: Optional[List[TaxRate]] = None
    shipping_methods: Optional[List[ShippingMethod]] = None
    maintenance_mode: Optional[bool] = None
    order_number_prefix: Optional[str] = None
    low_stock_alert_threshold: Optional[int] = None


class StoreSettingsResponse(BaseModel):
    id: str
    key: str
    store_name: str
    store_url: Optional[str] = None
    support_email: EmailStr
    support_phone: Optional[str] = None
    currency_code: str
    currency_symbol: str
    timezone: str
    tax_rates: List[TaxRate]
    shipping_methods: List[ShippingMethod]
    maintenance_mode: bool
    order_number_prefix: str
    low_stock_alert_threshold: int
