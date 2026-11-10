from datetime import datetime, timezone
from typing import Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.settings import StoreSettings
from app.repositories.base import BaseMongoRepository


class SettingsRepository(BaseMongoRepository[StoreSettings]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "settings", StoreSettings)

    async def get_settings(self) -> StoreSettings:
        doc = await self.find_one({"key": "global_store_settings"})
        if not doc:
            default_settings = StoreSettings()
            doc = await self.create(default_settings)
        return doc

    async def update_settings_data(self, update_data: Dict[str, Any]) -> StoreSettings:
        update_data["updated_at"] = datetime.now(timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"key": "global_store_settings"},
            {"$set": update_data},
            upsert=True,
            return_document=True,
        )
        return self._doc_to_model(doc)
