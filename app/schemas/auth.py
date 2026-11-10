from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.core.permissions import AdminRole
from app.models.admin import AdminStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AdminProfileResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: AdminRole
    status: AdminStatus
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    permissions: List[str]
    is_superadmin: bool
    last_login_at: Optional[datetime] = None
