from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.customer import Customer, CustomerStatus
from app.repositories.base import BaseMongoRepository


class CustomerRepository(BaseMongoRepository[Customer]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "customers", Customer)

    async def get_by_email(self, email: str) -> Optional[Customer]:
        return await self.find_one({"email": email.lower()})

    async def filter_customers(
        self,
        q: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        min_spent: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Customer], int]:
        query: Dict[str, Any] = {}
        if q:
            query["$or"] = [
                {"email": {"$regex": q, "$options": "i"}},
                {"first_name": {"$regex": q, "$options": "i"}},
                {"last_name": {"$regex": q, "$options": "i"}},
            ]
        if status:
            query["status"] = status
        if min_spent is not None:
            query["total_spent"] = {"$gte": min_spent}

        total = await self.count(query)
        items = await self.find_many(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("total_spent", -1)],
        )
        return items, total

    async def add_note(self, customer_id: str, note: str) -> Optional[Customer]:
        _id = self._parse_id(customer_id)
        result = await self.collection.find_one_and_update(
            {"_id": _id},
            {
                "$push": {"internal_notes": note},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def record_completed_order(self, customer_id: str, order_amount: float) -> None:
        _id = self._parse_id(customer_id)
        await self.collection.update_one(
            {"_id": _id},
            {
                "$inc": {"orders_count": 1, "total_spent": order_amount},
                "$set": {
                    "last_order_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            },
        )
