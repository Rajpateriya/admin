from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.inventory import StockAdjustmentReason, StockMovement
from app.repositories.base import BaseMongoRepository


class InventoryRepository(BaseMongoRepository[StockMovement]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "inventory_movements", StockMovement)

    async def record_movement(
        self,
        product_id: str,
        product_title: str,
        quantity_delta: int,
        previous_stock: int,
        new_stock: int,
        reason: StockAdjustmentReason,
        performed_by_id: str,
        performed_by_email: str,
        variant_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        movement = StockMovement(
            product_id=product_id,
            variant_id=variant_id,
            product_title=product_title,
            quantity_delta=quantity_delta,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=reason,
            reference_id=reference_id,
            performed_by_id=performed_by_id,
            performed_by_email=performed_by_email,
            notes=notes,
        )
        return await self.create(movement)

    async def get_movements(
        self,
        product_id: Optional[str] = None,
        reason: Optional[StockAdjustmentReason] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[StockMovement], int]:
        query: Dict[str, Any] = {}
        if product_id:
            query["product_id"] = product_id
        if reason:
            query["reason"] = reason

        total = await self.count(query)
        items = await self.find_many(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )
        return items, total
