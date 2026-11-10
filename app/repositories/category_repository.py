from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.category import Category
from app.repositories.base import BaseMongoRepository


class CategoryRepository(BaseMongoRepository[Category]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "categories", Category)

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        return await self.find_one({"slug": slug})

    async def get_tree(self) -> List[Dict[str, Any]]:
        """Fetch all categories and construct a parent-child hierarchical tree."""
        categories = await self.find_many({}, limit=500, sort=[("sort_order", 1), ("name", 1)])
        cat_map: Dict[str, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []

        for cat in categories:
            cat_dict = cat.model_dump(by_alias=False)
            cat_dict["children"] = []
            cat_map[str(cat.id)] = cat_dict

        for cat in categories:
            cat_id = str(cat.id)
            if cat.parent_id and cat.parent_id in cat_map:
                cat_map[cat.parent_id]["children"].append(cat_map[cat_id])
            else:
                roots.append(cat_map[cat_id])

        return roots
