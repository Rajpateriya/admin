from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.coupon import Coupon
from app.repositories.base import BaseMongoRepository


class CouponRepository(BaseMongoRepository[Coupon]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "coupons", Coupon)

    async def get_by_code(self, code: str) -> Optional[Coupon]:
        return await self.find_one({"code": code.upper().strip()})

    async def filter_coupons(
        self,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Coupon], int]:
        query: Dict[str, Any] = {}
        if is_active is not None:
            query["is_active"] = is_active

        total = await self.count(query)
        items = await self.find_many(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )
        return items, total

    async def increment_usage(self, coupon_id: str) -> None:
        _id = self._parse_id(coupon_id)
        await self.collection.update_one(
            {"_id": _id},
            {"$inc": {"usage_count": 1}},
        )
