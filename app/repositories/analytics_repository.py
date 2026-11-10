from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.order import OrderStatus, PaymentStatus
from app.models.product import ProductStatus
from app.schemas.analytics import DashboardOverviewResponse, OrderStatusCount, SalesTrendItem, TopProductItem


class AnalyticsRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_dashboard_overview(self) -> DashboardOverviewResponse:
        # 1. Total revenue and total orders
        revenue_pipeline = [
            {"$match": {"payment_status": {"$in": [PaymentStatus.PAID.value, PaymentStatus.AUTHORIZED.value]}}},
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$total_amount"},
                    "total_orders": {"$sum": 1},
                }
            },
        ]
        rev_cursor = self.db.orders.aggregate(revenue_pipeline)
        rev_res = await rev_cursor.to_list(length=1)

        total_revenue = round(rev_res[0]["total_revenue"], 2) if rev_res else 0.0
        total_orders = await self.db.orders.count_documents({})
        aov = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

        # 2. Customers and Products count
        total_customers = await self.db.customers.count_documents({})
        total_products = await self.db.products.count_documents({})

        # 3. Low stock products count
        low_stock_count = await self.db.products.count_documents({
            "status": ProductStatus.PUBLISHED.value,
            "$expr": {"$lte": ["$stock_quantity", "$low_stock_threshold"]},
        })

        # 4. Pending orders count
        pending_orders = await self.db.orders.count_documents({
            "status": {"$in": [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value]}
        })

        # 5. Orders by status
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        status_cursor = self.db.orders.aggregate(status_pipeline)
        status_res = await status_cursor.to_list(length=50)
        orders_by_status = [
            OrderStatusCount(status=str(doc["_id"]), count=doc["count"])
            for doc in status_res if doc["_id"] is not None
        ]

        # 6. Sales Trend (Past 14 days)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=14)
        trend_pipeline = [
            {"$match": {"created_at": {"$gte": cutoff_date}, "payment_status": PaymentStatus.PAID.value}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                        }
                    },
                    "revenue": {"$sum": "$total_amount"},
                    "orders_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        trend_cursor = self.db.orders.aggregate(trend_pipeline)
        trend_res = await trend_cursor.to_list(length=30)
        sales_trend = [
            SalesTrendItem(
                date=doc["_id"],
                revenue=round(doc["revenue"], 2),
                orders_count=doc["orders_count"],
            )
            for doc in trend_res if doc["_id"] is not None
        ]

        # 7. Top Selling Products
        top_products_pipeline = [
            {"$match": {"payment_status": PaymentStatus.PAID.value}},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.product_id",
                    "title": {"$first": "$items.title"},
                    "sku": {"$first": "$items.sku"},
                    "units_sold": {"$sum": "$items.quantity"},
                    "revenue": {"$sum": "$items.total_price"},
                }
            },
            {"$sort": {"units_sold": -1}},
            {"$limit": 5},
        ]
        top_cursor = self.db.orders.aggregate(top_products_pipeline)
        top_res = await top_cursor.to_list(length=5)
        top_selling = [
            TopProductItem(
                product_id=str(doc["_id"]),
                title=doc.get("title", "Unknown"),
                sku=doc.get("sku", "N/A"),
                units_sold=doc["units_sold"],
                revenue=round(doc["revenue"], 2),
            )
            for doc in top_res
        ]

        return DashboardOverviewResponse(
            total_revenue=total_revenue,
            total_orders=total_orders,
            average_order_value=aov,
            total_customers=total_customers,
            total_products=total_products,
            low_stock_products_count=low_stock_count,
            pending_orders_count=pending_orders,
            orders_by_status=orders_by_status,
            recent_sales_trend=sales_trend,
            top_selling_products=top_selling,
        )
