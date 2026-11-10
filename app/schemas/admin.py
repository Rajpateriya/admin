from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.core.permissions import AdminRole
from app.models.admin import AdminStatus


class AdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: str = Field(min_length=2)
    role: AdminRole = AdminRole.ADMIN
    phone: Optional[str] = None
    custom_permissions: List[str] = Field(default_factory=list)


class AdminUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[AdminRole] = None
    status: Optional[AdminStatus] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    custom_permissions: Optional[List[str]] = None


class AdminResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: AdminRole
    status: AdminStatus
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    custom_permissions: List[str] = Field(default_factory=list)
    is_superadmin: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PasswordChangeRequest(BaseModel):
    old_password: Optional[str] = None  # SuperAdmin can bypass old_password if forcing reset
    new_password: str = Field(min_length=8)
