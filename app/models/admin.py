from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import EmailStr, Field
from app.core.permissions import AdminRole
from app.models.base import BaseMongoModel


class AdminStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class Admin(BaseMongoModel):
    email: EmailStr
    hashed_password: str
    full_name: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    role: AdminRole = AdminRole.ADMIN
    status: AdminStatus = AdminStatus.ACTIVE
    custom_permissions: List[str] = Field(default_factory=list)
    last_login_at: Optional[datetime] = None
    is_superadmin: bool = False
    token_version: int = 1
