from typing import Any, Callable, Dict, List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.permissions import AdminRole, get_permissions_for_role
from app.core.security import decode_token
from app.models.admin import Admin, AdminStatus
from app.repositories.admin_repository import AdminRepository

security_bearer = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Admin:
    """Dependency that extracts, verifies and loads the current authenticated admin user."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authentication token is required.")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as e:
        raise UnauthorizedException(f"Invalid authentication token: {str(e)}")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type. Access token required.")

    admin_id = payload.get("sub")
    if not admin_id:
        raise UnauthorizedException("Malformed token: subject missing.")

    admin_repo = AdminRepository(db)
    admin = await admin_repo.get_by_id(admin_id)
    if not admin:
        raise UnauthorizedException("Admin account associated with this token does not exist.")

    if admin.status != AdminStatus.ACTIVE:
        raise ForbiddenException(f"Admin account is {admin.status.value.lower()}.")

    if admin.token_version > payload.get("token_version", 1):
        raise UnauthorizedException("Token has been revoked. Please authenticate again.")

    return admin


def get_current_admin_actor(
    admin: Admin = Depends(get_current_admin),
) -> Dict[str, Any]:
    """Helper returning a lightweight actor dictionary for audit logging and service calls."""
    permissions = list(get_permissions_for_role(admin.role, admin.custom_permissions))
    return {
        "id": str(admin.id),
        "email": admin.email,
        "role": admin.role.value,
        "is_superadmin": admin.is_superadmin,
        "permissions": permissions,
    }


def require_superadmin(
    admin: Admin = Depends(get_current_admin),
) -> Admin:
    """Enforce that the requesting admin has root SuperAdmin privileges."""
    if not admin.is_superadmin and admin.role != AdminRole.SUPERADMIN:
        raise ForbiddenException("Access restricted to platform SuperAdmins only.")
    return admin


def require_permissions(*required_permissions: str) -> Callable:
    """
    Factory dependency checking if current admin holds the required permission scopes.
    SuperAdmin ('*') automatically satisfies any requirement.
    """
    def permission_checker(admin: Admin = Depends(get_current_admin)) -> Admin:
        if admin.is_superadmin or admin.role == AdminRole.SUPERADMIN:
            return admin

        granted = get_permissions_for_role(admin.role, admin.custom_permissions)
        if "*" in granted:
            return admin

        missing = [p for p in required_permissions if p not in granted]
        if missing:
            raise ForbiddenException(
                f"You lack the required permission(s) for this action: {', '.join(missing)}"
            )
        return admin

    return permission_checker
