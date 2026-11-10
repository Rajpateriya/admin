from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.audit import AuditLog
from app.repositories.base import BaseMongoRepository


class AuditRepository(BaseMongoRepository[AuditLog]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "audit_logs", AuditLog)

    async def log_action(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        audit_entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details or {},
        )
        return await self.create(audit_entry)

    async def search_logs(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        query: Dict[str, Any] = {}
        if actor_id:
            query["actor_id"] = actor_id
        if action:
            query["action"] = action
        if resource_type:
            query["resource_type"] = resource_type

        total = await self.count(query)
        items = await self.find_many(
            query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )
        return items, total
