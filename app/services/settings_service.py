from typing import Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.audit_repository import AuditRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import StoreSettingsResponse, StoreSettingsUpdate


class SettingsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.settings_repo = SettingsRepository(db)
        self.audit_repo = AuditRepository(db)

    async def get_settings(self) -> StoreSettingsResponse:
        settings = await self.settings_repo.get_settings()
        return StoreSettingsResponse(**settings.model_dump(by_alias=False))

    async def update_settings(
        self,
        data: StoreSettingsUpdate,
        actor: Dict[str, Any],
    ) -> StoreSettingsResponse:
        patch = data.model_dump(exclude_unset=True)
        updated = await self.settings_repo.update_settings_data(patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_STORE_SETTINGS",
            resource_type="settings",
            details=patch,
        )
        return StoreSettingsResponse(**updated.model_dump(by_alias=False))
