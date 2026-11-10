from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.models.order import OrderStatus, PaymentStatus
from app.schemas.common import PaginatedResponse
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreateRequest,
    OrderNoteCreateRequest,
    OrderRefundRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderTrackingUpdateRequest,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Order & Fulfillment Management"])


@router.post("", response_model=OrderResponse)
async def create_order(
    payload: OrderCreateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """(Staff/Admin) Manually provision an order with item inventory reservation and coupon validation."""
    service = OrderService(db)
    return await service.create_order(payload, actor)


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    q: Optional[str] = Query(None, description="Search by order number, customer name, or customer email"),
    status: Optional[OrderStatus] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    min_total: Optional[float] = Query(None, ge=0),
    max_total: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_permissions(Permission.ORDERS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Search and filter customer orders with pagination."""
    service = OrderService(db)
    skip = (page - 1) * limit
    orders, total = await service.list_orders(
        q=q,
        status=status,
        payment_status=payment_status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        min_total=min_total,
        max_total=max_total,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse.create(items=orders, total=total, page=page, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    _: Admin = Depends(require_permissions(Permission.ORDERS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve full order details including line items, shipping address, and tracking data."""
    service = OrderService(db)
    return await service.get_order_by_id(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    payload: OrderStatusUpdateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Advance or update order state according to valid e-commerce lifecycle transitions."""
    service = OrderService(db)
    return await service.update_status(order_id, payload, actor)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    payload: OrderCancelRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Cancel an active order with reason and optional automatic warehouse stock restock."""
    service = OrderService(db)
    return await service.cancel_order(order_id, payload, actor)


@router.patch("/{order_id}/tracking", response_model=OrderResponse)
async def update_order_tracking(
    order_id: str,
    payload: OrderTrackingUpdateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update carrier shipment tracking information and auto-mark order as SHIPPED."""
    service = OrderService(db)
    return await service.update_tracking(order_id, payload, actor)


@router.post("/{order_id}/refund", response_model=OrderResponse)
async def refund_order(
    order_id: str,
    payload: OrderRefundRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_REFUND.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Issue a full or partial refund with optional automatic warehouse inventory restock."""
    service = OrderService(db)
    return await service.refund_order(order_id, payload, actor)


@router.post("/{order_id}/notes", response_model=OrderResponse)
async def add_order_note(
    order_id: str,
    payload: OrderNoteCreateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.ORDERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Append internal staff notes to an order."""
    service = OrderService(db)
    return await service.add_order_note(order_id, payload.note, actor)
