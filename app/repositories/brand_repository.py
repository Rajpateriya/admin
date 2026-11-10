from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.brand import Brand
from app.repositories.base import BaseMongoRepository


class BrandRepository(BaseMongoRepository[Brand]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "brands", Brand)

    async def get_by_slug(self, slug: str) -> Optional[Brand]:
        return await self.find_one({"slug": slug})
