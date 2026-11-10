from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.order import Order, OrderNote, OrderStatus, PaymentStatus, ShippingInfo
from app.repositories.base import BaseMongoRepository


class OrderRepository(BaseMongoRepository[Order]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "orders", Order)

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        return await self.find_one({"order_number": order_number})

    async def filter_orders(
        self,
        q: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        customer_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_total: Optional[float] = None,
        max_total: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        query: Dict[str, Any] = {}

        if q:
            query["$or"] = [
                {"order_number": {"$regex": q, "$options": "i"}},
                {"customer_email": {"$regex": q, "$options": "i"}},
                {"customer_name": {"$regex": q, "$options": "i"}},
            ]

        if status:
            query["status"] = status
        if payment_status:
            query["payment_status"] = payment_status
        if customer_id:
            query["customer_id"] = customer_id

        if date_from or date_to:
            date_query: Dict[str, Any] = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            query["created_at"] = date_query

        if min_total is not None or max_total is not None:
            total_query: Dict[str, Any] = {}
            if min_total is not None:
                total_query["$gte"] = min_total
            if max_total is not None:
                total_query["$lte"] = max_total
            query["total_amount"] = total_query

        total = await self.count(query)
        items = await self.find_many(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )
        return items, total

    async def add_admin_note(self, order_id: str, note: OrderNote) -> Optional[Order]:
        _id = self._parse_id(order_id)
        result = await self.collection.find_one_and_update(
            {"_id": _id},
            {
                "$push": {"admin_notes": note.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )
        return self._doc_to_model(result)

    async def update_tracking(self, order_id: str, shipping_info: ShippingInfo) -> Optional[Order]:
        _id = self._parse_id(order_id)
        result = await self.collection.find_one_and_update(
            {"_id": _id},
            {
                "$set": {
                    "shipping_info": shipping_info.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=True,
        )
        return self._doc_to_model(result)
