from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_superadmin
from app.core.database import get_database
from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminResponse, AdminUpdate, PasswordChangeRequest
from app.schemas.audit import AuditLogResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.settings import StoreSettingsResponse, StoreSettingsUpdate
from app.services.settings_service import SettingsService
from app.services.superadmin_service import SuperAdminService

router = APIRouter(prefix="/superadmin", tags=["SuperAdmin - Platform Management"])


# ===================== ADMIN ACCOUNTS MANAGEMENT =====================
@router.get("/admins", response_model=PaginatedResponse[AdminResponse])
async def list_admins(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) List all administrators in the system."""
    service = SuperAdminService(db)
    skip = (page - 1) * limit
    admins, total = await service.list_admins(skip=skip, limit=limit)
    return PaginatedResponse.create(items=admins, total=total, page=page, limit=limit)


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    payload: AdminCreate,
    request: Request,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Provision a new administrator with specific role and custom permissions."""
    service = SuperAdminService(db)
    client_ip = request.client.host if request.client else None
    return await service.create_admin(
        actor_id=actor["id"],
        actor_email=actor["email"],
        actor_role=actor["role"],
        create_data=payload,
        ip_address=client_ip,
    )


@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: str,
    payload: AdminUpdate,
    request: Request,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Modify role, status (ACTIVE/SUSPENDED), or custom permissions of an admin."""
    service = SuperAdminService(db)
    client_ip = request.client.host if request.client else None
    return await service.update_admin(
        actor_id=actor["id"],
        actor_email=actor["email"],
        actor_role=actor["role"],
        admin_id=admin_id,
        update_data=payload,
        ip_address=client_ip,
    )


@router.post("/admins/{admin_id}/reset-password", response_model=MessageResponse)
async def reset_admin_password(
    admin_id: str,
    payload: PasswordChangeRequest,
    request: Request,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Force reset an administrator's password."""
    service = SuperAdminService(db)
    client_ip = request.client.host if request.client else None
    await service.reset_password(
        actor_id=actor["id"],
        actor_email=actor["email"],
        actor_role=actor["role"],
        admin_id=admin_id,
        new_password=payload.new_password,
        ip_address=client_ip,
    )
    return MessageResponse(message="Administrator password reset successfully.")


@router.post("/admins/{admin_id}/revoke-tokens", response_model=MessageResponse)
async def revoke_admin_tokens(
    admin_id: str,
    request: Request,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Invalidate and revoke all active JWT tokens for an administrator."""
    service = SuperAdminService(db)
    client_ip = request.client.host if request.client else None
    await service.revoke_tokens(
        actor_id=actor["id"],
        actor_email=actor["email"],
        actor_role=actor["role"],
        admin_id=admin_id,
        ip_address=client_ip,
    )
    return MessageResponse(message="All active sessions and tokens for this administrator have been revoked.")


@router.delete("/admins/{admin_id}", response_model=MessageResponse)
async def delete_admin(
    admin_id: str,
    request: Request,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Delete an administrator account."""
    service = SuperAdminService(db)
    client_ip = request.client.host if request.client else None
    await service.delete_admin(
        actor_id=actor["id"],
        actor_email=actor["email"],
        actor_role=actor["role"],
        admin_id=admin_id,
        ip_address=client_ip,
    )
    return MessageResponse(message="Administrator deleted successfully.")


# ===================== AUDIT LOGS SURVEILLANCE =====================
@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Search immutable system activity and security audit trail."""
    service = SuperAdminService(db)
    skip = (page - 1) * limit
    logs, total = await service.get_audit_logs(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        skip=skip,
        limit=limit,
    )
    responses = [AuditLogResponse(**log.model_dump(by_alias=False)) for log in logs]
    return PaginatedResponse.create(items=responses, total=total, page=page, limit=limit)


@router.get("/audit-logs/export")
async def export_audit_logs(
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(5000, ge=1, le=10000),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Export system audit trail in CSV format for compliance reporting."""
    service = SuperAdminService(db)
    csv_content = await service.export_audit_logs_csv(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_logs_export.csv"'},
    )


# ===================== GLOBAL STORE CONFIGURATION =====================
@router.get("/settings", response_model=StoreSettingsResponse)
async def get_store_settings(
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) View global store configuration, currency, tax rates and shipping rules."""
    service = SettingsService(db)
    return await service.get_settings()


@router.put("/settings", response_model=StoreSettingsResponse)
async def update_store_settings(
    payload: StoreSettingsUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_superadmin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(SuperAdmin Only) Update global store settings, tax rates, currencies, or shipping methods."""
    service = SettingsService(db)
    return await service.update_settings(payload, actor)
