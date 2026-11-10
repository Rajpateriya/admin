from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.base import utc_now
from app.models.coupon import Coupon, DiscountType
from app.repositories.audit_repository import AuditRepository
from app.repositories.coupon_repository import CouponRepository
from app.schemas.coupon import (
    CouponCreate,
    CouponResponse,
    CouponStatsResponse,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidateResponse,
)


class CouponService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.coupon_repo = CouponRepository(db)
        self.audit_repo = AuditRepository(db)

    async def create_coupon(self, data: CouponCreate, actor: Dict[str, Any]) -> CouponResponse:
        code = data.code.strip().upper()
        existing = await self.coupon_repo.get_by_code(code)
        if existing:
            raise ConflictException(f"Coupon code '{code}' already exists.")

        valid_from = data.valid_from or utc_now()
        if data.valid_to <= valid_from:
            raise BadRequestException("Coupon 'valid_to' date must be after 'valid_from' date.")

        coupon = Coupon(
            code=code,
            discount_type=data.discount_type,
            value=data.value,
            min_order_amount=data.min_order_amount,
            max_discount_amount=data.max_discount_amount,
            usage_limit=data.usage_limit,
            per_customer_limit=data.per_customer_limit,
            valid_from=valid_from,
            valid_to=data.valid_to,
            is_active=data.is_active,
            applicable_category_ids=data.applicable_category_ids,
            applicable_product_ids=data.applicable_product_ids,
        )
        created = await self.coupon_repo.create(coupon)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_COUPON",
            resource_type="coupon",
            resource_id=str(created.id),
            details={"code": created.code, "value": created.value, "type": created.discount_type.value},
        )
        return CouponResponse(**created.model_dump(by_alias=False))

    async def update_coupon(self, coupon_id: str, data: CouponUpdate, actor: Dict[str, Any]) -> CouponResponse:
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon", coupon_id)

        patch = data.model_dump(exclude_unset=True)
        updated = await self.coupon_repo.update(coupon_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_COUPON",
            resource_type="coupon",
            resource_id=coupon_id,
            details=patch,
        )
        return CouponResponse(**updated.model_dump(by_alias=False))

    async def delete_coupon(self, coupon_id: str, actor: Dict[str, Any]) -> None:
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon", coupon_id)

        await self.coupon_repo.delete(coupon_id)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="DELETE_COUPON",
            resource_type="coupon",
            resource_id=coupon_id,
            details={"code": coupon.code},
        )

    async def list_coupons(
        self,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[CouponResponse], int]:
        coupons, total = await self.coupon_repo.filter_coupons(is_active=is_active, skip=skip, limit=limit)
        responses = [CouponResponse(**c.model_dump(by_alias=False)) for c in coupons]
        return responses, total

    async def get_coupon_by_id(self, coupon_id: str) -> CouponResponse:
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon", coupon_id)
        return CouponResponse(**coupon.model_dump(by_alias=False))

    async def validate_coupon(self, data: CouponValidateRequest) -> CouponValidateResponse:
        code = data.code.strip().upper()
        coupon = await self.coupon_repo.get_by_code(code)
        if not coupon:
            return CouponValidateResponse(
                valid=False,
                coupon_code=code,
                subtotal=data.order_subtotal,
                final_total=data.order_subtotal,
                message=f"Coupon code '{code}' does not exist.",
            )

        if not coupon.is_active:
            return CouponValidateResponse(
                valid=False,
                coupon_code=code,
                discount_type=coupon.discount_type,
                subtotal=data.order_subtotal,
                final_total=data.order_subtotal,
                message="Coupon is currently inactive.",
            )

        now = utc_now()
        valid_from = coupon.valid_from if coupon.valid_from.tzinfo else coupon.valid_from.replace(tzinfo=timezone.utc)
        valid_to = coupon.valid_to if coupon.valid_to.tzinfo else coupon.valid_to.replace(tzinfo=timezone.utc)
        if now < valid_from or now > valid_to:
            return CouponValidateResponse(
                valid=False,
                coupon_code=code,
                discount_type=coupon.discount_type,
                subtotal=data.order_subtotal,
                final_total=data.order_subtotal,
                message="Coupon has expired or is not yet active.",
            )

        if coupon.usage_limit is not None and coupon.usage_count >= coupon.usage_limit:
            return CouponValidateResponse(
                valid=False,
                coupon_code=code,
                discount_type=coupon.discount_type,
                subtotal=data.order_subtotal,
                final_total=data.order_subtotal,
                message="Coupon overall usage limit has been reached.",
            )

        if data.customer_id and coupon.per_customer_limit:
            cust_uses = await self.db.orders.count_documents({
                "customer_id": data.customer_id,
                "coupon_code": code,
                "status": {"$ne": "CANCELLED"},
            })
            if cust_uses >= coupon.per_customer_limit:
                return CouponValidateResponse(
                    valid=False,
                    coupon_code=code,
                    discount_type=coupon.discount_type,
                    subtotal=data.order_subtotal,
                    final_total=data.order_subtotal,
                    message=f"You have already reached the maximum usage limit ({coupon.per_customer_limit}) for this coupon.",
                )

        if coupon.min_order_amount is not None and data.order_subtotal < coupon.min_order_amount:
            return CouponValidateResponse(
                valid=False,
                coupon_code=code,
                discount_type=coupon.discount_type,
                subtotal=data.order_subtotal,
                final_total=data.order_subtotal,
                message=f"Minimum order spend of {coupon.min_order_amount:.2f} required to use this coupon.",
            )

        eligible_subtotal = data.order_subtotal
        if coupon.applicable_category_ids or coupon.applicable_product_ids:
            if data.items:
                matched_items = [
                    item for item in data.items
                    if (coupon.applicable_product_ids and item.product_id in coupon.applicable_product_ids)
                    or (coupon.applicable_category_ids and item.category_id in coupon.applicable_category_ids)
                ]
                if not matched_items:
                    return CouponValidateResponse(
                        valid=False,
                        coupon_code=code,
                        discount_type=coupon.discount_type,
                        subtotal=data.order_subtotal,
                        final_total=data.order_subtotal,
                        message="Coupon is not applicable to any items in your order.",
                    )
                eligible_subtotal = sum(i.quantity * i.unit_price for i in matched_items)

        discount = 0.0
        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount = (eligible_subtotal * coupon.value) / 100.0
            if coupon.max_discount_amount is not None:
                discount = min(discount, coupon.max_discount_amount)
        elif coupon.discount_type == DiscountType.FIXED_AMOUNT:
            discount = min(coupon.value, eligible_subtotal)
        elif coupon.discount_type == DiscountType.FREE_SHIPPING:
            discount = 0.0

        discount = round(discount, 2)
        final_total = max(0.0, round(data.order_subtotal - discount, 2))

        return CouponValidateResponse(
            valid=True,
            coupon_code=code,
            discount_type=coupon.discount_type,
            discount_amount=discount,
            subtotal=data.order_subtotal,
            final_total=final_total,
            message="Coupon applied successfully.",
        )

    async def get_coupon_stats(self, coupon_id: str) -> CouponStatsResponse:
        coupon = await self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon", coupon_id)

        pipeline = [
            {"$match": {"coupon_code": coupon.code, "status": {"$ne": "CANCELLED"}}},
            {
                "$group": {
                    "_id": None,
                    "total_discount": {"$sum": "$discount_amount"},
                    "total_revenue": {"$sum": "$total_amount"},
                }
            },
        ]
        res = await self.db.orders.aggregate(pipeline).to_list(length=1)
        tot_discount = round(res[0]["total_discount"], 2) if res else 0.0
        tot_revenue = round(res[0]["total_revenue"], 2) if res else 0.0

        return CouponStatsResponse(
            coupon_id=str(coupon.id),
            code=coupon.code,
            usage_count=coupon.usage_count,
            usage_limit=coupon.usage_limit,
            total_discount_given=tot_discount,
            total_orders_revenue=tot_revenue,
        )
