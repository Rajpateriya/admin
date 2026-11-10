from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.core.permissions import AdminRole
from app.core.security import hash_password
from app.models.admin import Admin, AdminStatus
from app.models.audit import AuditLog
from app.repositories.admin_repository import AdminRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.admin import AdminCreate, AdminResponse, AdminUpdate


class SuperAdminService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.admin_repo = AdminRepository(db)
        self.audit_repo = AuditRepository(db)

    async def list_admins(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[AdminResponse], int]:
        total = await self.admin_repo.count({})
        admins = await self.admin_repo.find_many({}, skip=skip, limit=limit, sort=[("created_at", -1)])
        responses = [
            AdminResponse(
                id=str(a.id),
                email=a.email,
                full_name=a.full_name,
                role=a.role,
                status=a.status,
                phone=a.phone,
                avatar_url=a.avatar_url,
                custom_permissions=a.custom_permissions,
                is_superadmin=a.is_superadmin,
                last_login_at=a.last_login_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in admins
        ]
        return responses, total

    async def create_admin(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        create_data: AdminCreate,
        ip_address: Optional[str] = None,
    ) -> AdminResponse:
        existing = await self.admin_repo.get_by_email(create_data.email)
        if existing:
            raise ConflictException(f"An admin with email '{create_data.email}' already exists.")

        is_super = create_data.role == AdminRole.SUPERADMIN
        hashed_pwd = hash_password(create_data.password)

        new_admin = Admin(
            email=create_data.email.lower(),
            hashed_password=hashed_pwd,
            full_name=create_data.full_name,
            role=create_data.role,
            status=AdminStatus.ACTIVE,
            phone=create_data.phone,
            custom_permissions=create_data.custom_permissions,
            is_superadmin=is_super,
        )
        created = await self.admin_repo.create(new_admin)

        # Audit event
        await self.audit_repo.log_action(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action="CREATE_ADMIN",
            resource_type="admin",
            resource_id=str(created.id),
            ip_address=ip_address,
            details={"email": created.email, "role": created.role.value},
        )

        return AdminResponse(
            id=str(created.id),
            email=created.email,
            full_name=created.full_name,
            role=created.role,
            status=created.status,
            phone=created.phone,
            avatar_url=created.avatar_url,
            custom_permissions=created.custom_permissions,
            is_superadmin=created.is_superadmin,
            last_login_at=created.last_login_at,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def update_admin(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        admin_id: str,
        update_data: AdminUpdate,
        ip_address: Optional[str] = None,
    ) -> AdminResponse:
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise NotFoundException("Admin", admin_id)

        # Prevent removing superadmin status from oneself
        if str(admin.id) == actor_id and update_data.role and update_data.role != AdminRole.SUPERADMIN:
            raise BadRequestException("You cannot revoke your own SuperAdmin role.")

        patch = update_data.model_dump(exclude_unset=True)
        if "role" in patch and patch["role"] == AdminRole.SUPERADMIN:
            patch["is_superadmin"] = True
        elif "role" in patch and patch["role"] != AdminRole.SUPERADMIN:
            patch["is_superadmin"] = False

        if "status" in patch and patch["status"] in [AdminStatus.INACTIVE, AdminStatus.SUSPENDED]:
            patch["token_version"] = admin.token_version + 1

        updated = await self.admin_repo.update(admin_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action="UPDATE_ADMIN",
            resource_type="admin",
            resource_id=admin_id,
            ip_address=ip_address,
            details=patch,
        )

        return AdminResponse(
            id=str(updated.id),
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role,
            status=updated.status,
            phone=updated.phone,
            avatar_url=updated.avatar_url,
            custom_permissions=updated.custom_permissions,
            is_superadmin=updated.is_superadmin,
            last_login_at=updated.last_login_at,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    async def reset_password(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        admin_id: str,
        new_password: str,
        ip_address: Optional[str] = None,
    ) -> None:
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise NotFoundException("Admin", admin_id)

        hashed = hash_password(new_password)
        await self.admin_repo.update(
            admin_id,
            {
                "hashed_password": hashed,
                "token_version": admin.token_version + 1,
            },
        )

        await self.audit_repo.log_action(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action="RESET_ADMIN_PASSWORD",
            resource_type="admin",
            resource_id=admin_id,
            ip_address=ip_address,
            details={"admin_email": admin.email},
        )

    async def revoke_tokens(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        admin_id: str,
        ip_address: Optional[str] = None,
    ) -> None:
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise NotFoundException("Admin", admin_id)

        await self.admin_repo.update(admin_id, {"token_version": admin.token_version + 1})

        await self.audit_repo.log_action(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action="REVOKE_ADMIN_TOKENS",
            resource_type="admin",
            resource_id=admin_id,
            ip_address=ip_address,
            details={"admin_email": admin.email, "revoked_at_version": admin.token_version + 1},
        )

    async def delete_admin(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        admin_id: str,
        ip_address: Optional[str] = None,
    ) -> None:
        admin = await self.admin_repo.get_by_id(admin_id)
        if not admin:
            raise NotFoundException("Admin", admin_id)

        if str(admin.id) == actor_id:
            raise BadRequestException("You cannot delete your own account.")

        if admin.is_superadmin and admin.email == "superadmin@ecommerce.com":
            raise ForbiddenException("Primary Root SuperAdmin cannot be deleted.")

        await self.admin_repo.delete(admin_id)

        await self.audit_repo.log_action(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action="DELETE_ADMIN",
            resource_type="admin",
            resource_id=admin_id,
            ip_address=ip_address,
            details={"deleted_email": admin.email, "role": admin.role.value},
        )

    async def get_audit_logs(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        return await self.audit_repo.search_logs(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            skip=skip,
            limit=limit,
        )

    async def export_audit_logs_csv(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 5000,
    ) -> str:
        import csv
        import io
        import json

        logs, _ = await self.audit_repo.search_logs(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            skip=0,
            limit=limit,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID",
            "Timestamp",
            "Actor ID",
            "Actor Email",
            "Actor Role",
            "Action",
            "Resource Type",
            "Resource ID",
            "IP Address",
            "Details",
        ])

        for log in logs:
            writer.writerow([
                str(log.id),
                log.created_at.isoformat() if log.created_at else "",
                log.actor_id,
                log.actor_email,
                log.actor_role,
                log.action,
                log.resource_type,
                log.resource_id or "",
                log.ip_address or "",
                json.dumps(log.details or {}),
            ])

        return output.getvalue()
