from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.admin import Admin
from app.repositories.base import BaseMongoRepository


class AdminRepository(BaseMongoRepository[Admin]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "admins", Admin)

    async def get_by_email(self, email: str) -> Optional[Admin]:
        return await self.find_one({"email": email.lower()})

    async def update_last_login(self, admin_id: str) -> None:
        _id = self._parse_id(admin_id)
        await self.collection.update_one(
            {"_id": _id},
            {"$set": {"last_login_at": datetime.now(timezone.utc)}},
        )
