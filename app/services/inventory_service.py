from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.inventory import StockAdjustmentReason
from app.repositories.audit_repository import AuditRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.inventory import LowStockAlertResponse, StockAdjustmentCreate, StockMovementResponse


class InventoryService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.audit_repo = AuditRepository(db)

    async def adjust_stock(
        self,
        data: StockAdjustmentCreate,
        actor: Dict[str, Any],
    ) -> StockMovementResponse:
        product = await self.product_repo.get_by_id(data.product_id)
        if not product:
            raise NotFoundException("Product", data.product_id)

        target_variant = None
        if data.variant_id:
            for v in product.variants:
                if v.id == data.variant_id:
                    target_variant = v
                    break
            if not target_variant:
                raise NotFoundException("Product Variant", data.variant_id)

        previous_stock = target_variant.stock_quantity if target_variant else product.stock_quantity
        new_stock = previous_stock + data.quantity_delta

        if new_stock < 0:
            raise BadRequestException(
                f"Insufficient stock to reduce by {abs(data.quantity_delta)}. Current stock: {previous_stock}."
            )

        # Update product stock atomically
        await self.product_repo.update_stock(
            product_id=data.product_id,
            variant_id=data.variant_id,
            delta=data.quantity_delta,
        )

        # Record movement
        movement = await self.inventory_repo.record_movement(
            product_id=data.product_id,
            product_title=product.title,
            variant_id=data.variant_id,
            quantity_delta=data.quantity_delta,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=data.reason,
            reference_id=data.reference_id,
            performed_by_id=actor["id"],
            performed_by_email=actor["email"],
            notes=data.notes,
        )

        # Audit
        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="ADJUST_STOCK",
            resource_type="inventory",
            resource_id=data.product_id,
            details={
                "product_title": product.title,
                "variant_id": data.variant_id,
                "delta": data.quantity_delta,
                "previous_stock": previous_stock,
                "new_stock": new_stock,
                "reason": data.reason.value,
            },
        )

        return StockMovementResponse(**movement.model_dump(by_alias=False))

    async def get_low_stock_alerts(self, limit: int = 50) -> List[LowStockAlertResponse]:
        products = await self.product_repo.get_low_stock_products(limit=limit)
        alerts: List[LowStockAlertResponse] = []

        for p in products:
            if p.variants:
                for v in p.variants:
                    if v.stock_quantity <= p.low_stock_threshold:
                        alerts.append(
                            LowStockAlertResponse(
                                product_id=str(p.id),
                                title=p.title,
                                sku=v.sku,
                                stock_quantity=v.stock_quantity,
                                low_stock_threshold=p.low_stock_threshold,
                                variant_id=v.id,
                                variant_title=v.title,
                            )
                        )
            else:
                alerts.append(
                    LowStockAlertResponse(
                        product_id=str(p.id),
                        title=p.title,
                        sku=p.sku,
                        stock_quantity=p.stock_quantity,
                        low_stock_threshold=p.low_stock_threshold,
                    )
                )

        return alerts

    async def get_movement_history(
        self,
        product_id: Optional[str] = None,
        reason: Optional[StockAdjustmentReason] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[StockMovementResponse], int]:
        movements, total = await self.inventory_repo.get_movements(
            product_id=product_id,
            reason=reason,
            skip=skip,
            limit=limit,
        )
        responses = [StockMovementResponse(**m.model_dump(by_alias=False)) for m in movements]
        return responses, total
