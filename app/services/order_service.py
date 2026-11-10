import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.base import utc_now
from app.models.inventory import StockAdjustmentReason
from app.models.order import Order, OrderItem, OrderNote, OrderStatus, PaymentStatus, ShippingInfo
from app.repositories.audit_repository import AuditRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreateRequest,
    OrderRefundRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderTrackingUpdateRequest,
)

# Explicit state transition graph
VALID_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


class OrderService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.audit_repo = AuditRepository(db)

    async def list_orders(
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
    ) -> Tuple[List[OrderResponse], int]:
        orders, total = await self.order_repo.filter_orders(
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
        responses = [OrderResponse(**o.model_dump(by_alias=False)) for o in orders]
        return responses, total

    async def get_order_by_id(self, order_id: str) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)
        return OrderResponse(**order.model_dump(by_alias=False))

    async def update_status(
        self,
        order_id: str,
        update_data: OrderStatusUpdateRequest,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)

        target_status = update_data.status
        allowed = VALID_TRANSITIONS.get(order.status, set())

        if target_status not in allowed:
            raise BadRequestException(
                f"Invalid order status transition from '{order.status.value}' to '{target_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

        patch: Dict[str, Any] = {"status": target_status.value}

        if target_status == OrderStatus.CANCELLED:
            patch["cancellation_reason"] = update_data.reason or "Cancelled by administrative staff"

        if target_status == OrderStatus.DELIVERED and order.payment_status == PaymentStatus.AUTHORIZED:
            patch["payment_status"] = PaymentStatus.PAID.value

        updated = await self.order_repo.update(order_id, patch)

        # If delivered and paid, record customer completed order metrics
        if target_status == OrderStatus.DELIVERED and order.customer_id:
            await self.customer_repo.record_completed_order(order.customer_id, order.total_amount)

        # Audit
        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_ORDER_STATUS",
            resource_type="order",
            resource_id=order_id,
            details={
                "order_number": order.order_number,
                "from_status": order.status.value,
                "to_status": target_status.value,
                "reason": update_data.reason,
            },
        )
        return OrderResponse(**updated.model_dump(by_alias=False))

    async def update_tracking(
        self,
        order_id: str,
        data: OrderTrackingUpdateRequest,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)

        shipping_info = ShippingInfo(
            carrier=data.carrier,
            tracking_number=data.tracking_number,
            tracking_url=data.tracking_url,
            shipped_at=datetime.now(timezone.utc),
        )
        updated = await self.order_repo.update_tracking(order_id, shipping_info)

        # If order was PROCESSING, auto-progress to SHIPPED
        if order.status == OrderStatus.PROCESSING:
            updated = await self.order_repo.update(order_id, {"status": OrderStatus.SHIPPED.value})

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_ORDER_TRACKING",
            resource_type="order",
            resource_id=order_id,
            details={
                "order_number": order.order_number,
                "carrier": data.carrier,
                "tracking_number": data.tracking_number,
            },
        )
        return OrderResponse(**updated.model_dump(by_alias=False))

    async def refund_order(
        self,
        order_id: str,
        data: OrderRefundRequest,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)

        remaining_refundable = order.total_amount - order.refunded_amount
        if data.amount > remaining_refundable:
            raise BadRequestException(
                f"Refund amount {data.amount} exceeds remaining refundable balance of {remaining_refundable:.2f}."
            )

        new_refunded_total = order.refunded_amount + data.amount
        is_full_refund = new_refunded_total >= order.total_amount

        patch = {
            "refunded_amount": new_refunded_total,
            "payment_status": PaymentStatus.REFUNDED.value if is_full_refund else PaymentStatus.PARTIALLY_REFUNDED.value,
        }
        if is_full_refund:
            patch["status"] = OrderStatus.REFUNDED.value

        updated = await self.order_repo.update(order_id, patch)

        # Optional Inventory Restock
        if data.restock_inventory:
            for item in order.items:
                product = await self.product_repo.get_by_id(item.product_id)
                if product:
                    prev_stock = product.stock_quantity
                    await self.product_repo.update_stock(item.product_id, item.variant_id, item.quantity)
                    await self.inventory_repo.record_movement(
                        product_id=item.product_id,
                        product_title=item.title,
                        variant_id=item.variant_id,
                        quantity_delta=item.quantity,
                        previous_stock=prev_stock,
                        new_stock=prev_stock + item.quantity,
                        reason=StockAdjustmentReason.CUSTOMER_RETURN,
                        reference_id=order.order_number,
                        performed_by_id=actor["id"],
                        performed_by_email=actor["email"],
                        notes=f"Restocked upon refund for order {order.order_number}: {data.reason}",
                    )

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="REFUND_ORDER",
            resource_type="order",
            resource_id=order_id,
            details={
                "order_number": order.order_number,
                "refund_amount": data.amount,
                "reason": data.reason,
                "restocked": data.restock_inventory,
                "is_full_refund": is_full_refund,
            },
        )
        return OrderResponse(**updated.model_dump(by_alias=False))

    async def create_order(
        self,
        data: OrderCreateRequest,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        prefix = "ORD"
        settings_doc = await self.db.settings.find_one({"key": "global_store_settings"})
        if settings_doc and settings_doc.get("order_number_prefix"):
            prefix = settings_doc["order_number_prefix"]

        now = utc_now()
        random_suffix = uuid.uuid4().hex[:6].upper()
        order_number = f"{prefix}-{now.strftime('%Y%m%d')}-{random_suffix}"

        order_items: List[OrderItem] = []
        subtotal = 0.0

        for item_in in data.items:
            product = await self.product_repo.get_by_id(item_in.product_id)
            if not product:
                raise NotFoundException("Product", item_in.product_id)

            variant = None
            if item_in.variant_id:
                for v in product.variants:
                    if v.id == item_in.variant_id:
                        variant = v
                        break
                if not variant:
                    raise NotFoundException("Product Variant", item_in.variant_id)

            avail_stock = variant.stock_quantity if variant else product.stock_quantity
            if avail_stock < item_in.quantity:
                item_name = f"{product.title} ({variant.title})" if variant else product.title
                raise BadRequestException(
                    f"Insufficient stock for '{item_name}'. Available: {avail_stock}, requested: {item_in.quantity}."
                )

            unit_price = item_in.unit_price if item_in.unit_price is not None else (variant.price if variant else product.base_price)
            item_total = round(unit_price * item_in.quantity, 2)
            subtotal += item_total

            sku = variant.sku if variant else product.sku
            title = f"{product.title} - {variant.title}" if variant else product.title
            image_url = variant.image_url if variant and variant.image_url else (product.images[0] if product.images else None)

            order_items.append(
                OrderItem(
                    product_id=str(product.id),
                    variant_id=variant.id if variant else None,
                    title=title,
                    sku=sku,
                    quantity=item_in.quantity,
                    unit_price=unit_price,
                    total_price=item_total,
                    image_url=image_url,
                )
            )

            prev_stock = avail_stock
            await self.product_repo.update_stock(str(product.id), variant.id if variant else None, -item_in.quantity)
            await self.inventory_repo.record_movement(
                product_id=str(product.id),
                product_title=title,
                variant_id=variant.id if variant else None,
                quantity_delta=-item_in.quantity,
                previous_stock=prev_stock,
                new_stock=prev_stock - item_in.quantity,
                reason=StockAdjustmentReason.ORDER_FULFILLMENT,
                reference_id=order_number,
                performed_by_id=actor["id"],
                performed_by_email=actor["email"],
                notes=f"Reserved for order {order_number}",
            )

        discount_amount = 0.0
        applied_coupon = None
        if data.coupon_code:
            from app.schemas.coupon import CartItem, CouponValidateRequest
            from app.services.coupon_service import CouponService

            coupon_service = CouponService(self.db)
            val_res = await coupon_service.validate_coupon(
                CouponValidateRequest(
                    code=data.coupon_code,
                    order_subtotal=subtotal,
                    customer_id=data.customer_id,
                    items=[
                        CartItem(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price)
                        for i in order_items
                    ],
                )
            )
            if val_res.valid:
                discount_amount = val_res.discount_amount
                applied_coupon = val_res.coupon_code
                coupon_doc = await self.db.coupons.find_one({"code": applied_coupon})
                if coupon_doc:
                    await self.db.coupons.update_one({"_id": coupon_doc["_id"]}, {"$inc": {"usage_count": 1}})

        subtotal = round(subtotal, 2)
        total_amount = max(0.0, round(subtotal - discount_amount + data.tax_amount + data.shipping_amount, 2))

        cust_id = data.customer_id or str(uuid.uuid4())
        existing_cust = await self.customer_repo.get_by_email(data.customer_email)
        if existing_cust:
            cust_id = str(existing_cust.id)

        billing_addr = data.billing_address or data.shipping_address
        notes_list = []
        if data.notes:
            notes_list.append(
                OrderNote(
                    author_id=actor["id"],
                    author_email=actor["email"],
                    note=data.notes,
                    created_at=now,
                )
            )

        new_order = Order(
            order_number=order_number,
            customer_id=cust_id,
            customer_email=data.customer_email.lower(),
            customer_name=data.customer_name,
            items=order_items,
            shipping_address=data.shipping_address,
            billing_address=billing_addr,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.UNPAID,
            payment_method=data.payment_method,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=data.tax_amount,
            shipping_amount=data.shipping_amount,
            total_amount=total_amount,
            coupon_code=applied_coupon,
            admin_notes=notes_list,
        )
        created_order = await self.order_repo.create(new_order)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_ORDER",
            resource_type="order",
            resource_id=str(created_order.id),
            details={
                "order_number": order_number,
                "total_amount": total_amount,
                "items_count": len(order_items),
            },
        )
        return OrderResponse(**created_order.model_dump(by_alias=False))

    async def cancel_order(
        self,
        order_id: str,
        data: OrderCancelRequest,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)

        if order.status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
            raise BadRequestException(f"Order cannot be cancelled from '{order.status.value}' state.")

        patch = {
            "status": OrderStatus.CANCELLED.value,
            "cancellation_reason": data.reason,
        }
        updated = await self.order_repo.update(order_id, patch)

        if data.restock_inventory and order.status != OrderStatus.DELIVERED:
            for item in order.items:
                product = await self.product_repo.get_by_id(item.product_id)
                if product:
                    prev_stock = product.stock_quantity
                    await self.product_repo.update_stock(item.product_id, item.variant_id, item.quantity)
                    await self.inventory_repo.record_movement(
                        product_id=item.product_id,
                        product_title=item.title,
                        variant_id=item.variant_id,
                        quantity_delta=item.quantity,
                        previous_stock=prev_stock,
                        new_stock=prev_stock + item.quantity,
                        reason=StockAdjustmentReason.CUSTOMER_RETURN,
                        reference_id=order.order_number,
                        performed_by_id=actor["id"],
                        performed_by_email=actor["email"],
                        notes=f"Restocked upon order cancellation: {data.reason}",
                    )

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CANCEL_ORDER",
            resource_type="order",
            resource_id=order_id,
            details={
                "order_number": order.order_number,
                "reason": data.reason,
                "restocked": data.restock_inventory,
            },
        )
        return OrderResponse(**updated.model_dump(by_alias=False))

    async def add_order_note(
        self,
        order_id: str,
        note_text: str,
        actor: Dict[str, Any],
    ) -> OrderResponse:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException("Order", order_id)

        note = OrderNote(
            author_id=actor["id"],
            author_email=actor["email"],
            note=note_text,
            created_at=utc_now(),
        )
        updated = await self.order_repo.add_admin_note(order_id, note)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="ADD_ORDER_NOTE",
            resource_type="order",
            resource_id=order_id,
            details={"order_number": order.order_number, "note": note_text},
        )
        return OrderResponse(**updated.model_dump(by_alias=False))
