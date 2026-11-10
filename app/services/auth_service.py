from typing import Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, UnauthorizedException
from app.core.permissions import get_permissions_for_role
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.admin import AdminStatus
from app.repositories.admin_repository import AdminRepository
from app.schemas.auth import AdminProfileResponse, TokenResponse


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.admin_repo = AdminRepository(db)

    async def authenticate_admin(self, email: str, password: str) -> TokenResponse:
        admin = await self.admin_repo.get_by_email(email)
        if not admin or not verify_password(password, admin.hashed_password):
            raise UnauthorizedException("Invalid email or password.")

        if admin.status != AdminStatus.ACTIVE:
            raise ForbiddenException(f"Account is {admin.status.value.lower()}. Please contact SuperAdmin.")

        permissions = list(get_permissions_for_role(admin.role, admin.custom_permissions))
        access_token = create_access_token(
            subject=str(admin.id),
            role=admin.role.value,
            permissions=permissions,
            token_version=admin.token_version,
        )
        refresh_token = create_refresh_token(
            subject=str(admin.id),
            token_version=admin.token_version,
        )

        await self.admin_repo.update_last_login(str(admin.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type")
            admin_id = payload.get("sub")
        except Exception:
            raise UnauthorizedException("Invalid or expired refresh token")

        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin or admin.status != AdminStatus.ACTIVE:
            raise UnauthorizedException("Admin not found or inactive")

        if admin.token_version > payload.get("token_version", 1):
            raise UnauthorizedException("Refresh token has been revoked")

        permissions = list(get_permissions_for_role(admin.role, admin.custom_permissions))
        new_access_token = create_access_token(
            subject=str(admin.id),
            role=admin.role.value,
            permissions=permissions,
            token_version=admin.token_version,
        )
        new_refresh_token = create_refresh_token(
            subject=str(admin.id),
            token_version=admin.token_version,
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    async def get_admin_profile(self, admin_id: str) -> AdminProfileResponse:
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise UnauthorizedException("Admin account not found")

        permissions = list(get_permissions_for_role(admin.role, admin.custom_permissions))
        return AdminProfileResponse(
            id=str(admin.id),
            email=admin.email,
            full_name=admin.full_name,
            role=admin.role,
            status=admin.status,
            avatar_url=admin.avatar_url,
            phone=admin.phone,
            permissions=permissions,
            is_superadmin=admin.is_superadmin,
            last_login_at=admin.last_login_at,
        )
