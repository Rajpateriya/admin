from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.coupon import (
    CouponCreate,
    CouponResponse,
    CouponStatsResponse,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["Marketing & Promotion Engine"])


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    payload: CouponValidateRequest,
    _: Admin = Depends(require_permissions(Permission.COUPONS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Validate promotional coupon code against an active order/cart.
    Checks date windows, usage limits, per-customer limits, minimum spend,
    and product/category eligibility, returning exact discount calculations.
    """
    service = CouponService(db)
    return await service.validate_coupon(payload)


@router.get("", response_model=PaginatedResponse[CouponResponse])
async def list_coupons(
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_permissions(Permission.COUPONS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List discount coupons and promotion campaigns with active status filtering."""
    service = CouponService(db)
    skip = (page - 1) * limit
    coupons, total = await service.list_coupons(is_active=is_active, skip=skip, limit=limit)
    return PaginatedResponse.create(items=coupons, total=total, page=page, limit=limit)


@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: str,
    _: Admin = Depends(require_permissions(Permission.COUPONS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve detailed coupon configuration."""
    service = CouponService(db)
    return await service.get_coupon_by_id(coupon_id)


@router.get("/{coupon_id}/stats", response_model=CouponStatsResponse)
async def get_coupon_stats(
    coupon_id: str,
    _: Admin = Depends(require_permissions(Permission.COUPONS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve performance metrics, redemptions count, and sales revenue impact for a promotion."""
    service = CouponService(db)
    return await service.get_coupon_stats(coupon_id)


@router.post("", response_model=CouponResponse)
async def create_coupon(
    payload: CouponCreate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.COUPONS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new promotional coupon code with spend rules and validity limits."""
    service = CouponService(db)
    return await service.create_coupon(payload, actor)


@router.put("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: str,
    payload: CouponUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.COUPONS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update coupon configuration, validity window, or discount amount."""
    service = CouponService(db)
    return await service.update_coupon(coupon_id, payload, actor)


@router.delete("/{coupon_id}", response_model=MessageResponse)
async def delete_coupon(
    coupon_id: str,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.COUPONS_DELETE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Permanently delete a coupon code."""
    service = CouponService(db)
    await service.delete_coupon(coupon_id, actor)
    return MessageResponse(message="Coupon deleted successfully.")
