from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.models.inventory import StockAdjustmentReason
from app.schemas.common import PaginatedResponse
from app.schemas.inventory import LowStockAlertResponse, StockAdjustmentCreate, StockMovementResponse
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory & Warehouse Management"])


@router.get("/alerts/low-stock", response_model=List[LowStockAlertResponse])
async def get_low_stock_alerts(
    limit: int = Query(50, ge=1, le=200),
    _: Admin = Depends(require_permissions(Permission.INVENTORY_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve real-time alert list of all items where inventory has dropped to or below alert threshold."""
    service = InventoryService(db)
    return await service.get_low_stock_alerts(limit=limit)


@router.get("/history", response_model=PaginatedResponse[StockMovementResponse])
async def get_stock_movement_history(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    reason: Optional[StockAdjustmentReason] = Query(None, description="Filter by adjustment reason"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_permissions(Permission.INVENTORY_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """View paginated historical stock movement and audit trail across all SKUs."""
    service = InventoryService(db)
    skip = (page - 1) * limit
    items, total = await service.get_movement_history(
        product_id=product_id,
        reason=reason,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("/adjust", response_model=StockMovementResponse)
async def adjust_stock(
    payload: StockAdjustmentCreate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.INVENTORY_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Perform an atomic inventory adjustment (+ or -) with mandatory audit reason code."""
    service = InventoryService(db)
    return await service.adjust_stock(payload, actor)
