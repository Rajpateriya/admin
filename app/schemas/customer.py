from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.customer import Address, CustomerStatus


class CustomerCreateRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone: Optional[str] = None
    addresses: List[Address] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class CustomerUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    addresses: Optional[List[Address]] = None


class CustomerStatusUpdateRequest(BaseModel):
    status: CustomerStatus


class CustomerNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1)


class CustomerResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    status: CustomerStatus
    addresses: List[Address] = Field(default_factory=list)
    orders_count: int
    total_spent: float
    last_order_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    internal_notes: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
