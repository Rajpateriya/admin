from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.base import BaseMongoModel


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    FLAGGED = "FLAGGED"


class Address(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    company: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    is_default: bool = False


class Customer(BaseMongoModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    status: CustomerStatus = CustomerStatus.ACTIVE
    addresses: List[Address] = Field(default_factory=list)
    orders_count: int = Field(default=0, ge=0)
    total_spent: float = Field(default=0.0, ge=0)
    last_order_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    internal_notes: List[str] = Field(default_factory=list)
