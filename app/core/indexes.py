import logging
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("uvicorn.error")


async def create_indexes(db: AsyncIOMotorDatabase):
    """
    Ensure all necessary MongoDB indexes are created for optimal read performance
    and data integrity across all e-commerce domain collections.
    """
    logger.info("Verifying and creating MongoDB indexes for high-throughput scalability...")
    try:
        # 1. Admins Collection Indexes
        await db.admins.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True, name="idx_admin_email_unique"),
            IndexModel([("role", ASCENDING)], name="idx_admin_role"),
            IndexModel([("status", ASCENDING)], name="idx_admin_status"),
        ])

        # 2. Categories Collection Indexes
        await db.categories.create_indexes([
            IndexModel([("slug", ASCENDING)], unique=True, name="idx_category_slug_unique"),
            IndexModel([("parent_id", ASCENDING)], name="idx_category_parent"),
            IndexModel([("is_active", ASCENDING)], name="idx_category_active"),
        ])

        # 3. Brands Collection Indexes
        await db.brands.create_indexes([
            IndexModel([("slug", ASCENDING)], unique=True, name="idx_brand_slug_unique"),
            IndexModel([("is_active", ASCENDING)], name="idx_brand_active"),
        ])

        # 4. Products Collection Indexes
        await db.products.create_indexes([
            IndexModel([("sku", ASCENDING)], unique=True, sparse=True, name="idx_product_sku_unique"),
            IndexModel([("slug", ASCENDING)], unique=True, name="idx_product_slug_unique"),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="idx_product_status_created"),
            IndexModel([("category_id", ASCENDING)], name="idx_product_category"),
            IndexModel([("brand_id", ASCENDING)], name="idx_product_brand"),
            IndexModel([("stock_quantity", ASCENDING)], name="idx_product_stock"),
            IndexModel([("title", TEXT), ("description", TEXT), ("tags", TEXT)], name="idx_product_text_search"),
        ])

        # 5. Inventory Movements Collection Indexes
        await db.inventory_movements.create_indexes([
            IndexModel([("product_id", ASCENDING), ("created_at", DESCENDING)], name="idx_inventory_product_created"),
            IndexModel([("created_at", DESCENDING)], name="idx_inventory_created"),
            IndexModel([("reason", ASCENDING)], name="idx_inventory_reason"),
        ])

        # 6. Orders Collection Indexes
        await db.orders.create_indexes([
            IndexModel([("order_number", ASCENDING)], unique=True, name="idx_order_number_unique"),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="idx_order_status_created"),
            IndexModel([("payment_status", ASCENDING)], name="idx_order_payment_status"),
            IndexModel([("customer_id", ASCENDING), ("created_at", DESCENDING)], name="idx_order_customer"),
            IndexModel([("created_at", DESCENDING)], name="idx_order_created_desc"),
        ])

        # 7. Customers Collection Indexes
        await db.customers.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True, name="idx_customer_email_unique"),
            IndexModel([("status", ASCENDING)], name="idx_customer_status"),
            IndexModel([("total_spent", DESCENDING)], name="idx_customer_total_spent"),
            IndexModel([("created_at", DESCENDING)], name="idx_customer_created"),
        ])

        # 8. Coupons Collection Indexes
        await db.coupons.create_indexes([
            IndexModel([("code", ASCENDING)], unique=True, name="idx_coupon_code_unique"),
            IndexModel([("is_active", ASCENDING), ("valid_to", ASCENDING)], name="idx_coupon_active_validity"),
        ])

        # 9. Audit Logs Collection Indexes
        await db.audit_logs.create_indexes([
            IndexModel([("created_at", DESCENDING)], name="idx_audit_created_desc"),
            IndexModel([("actor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_audit_actor"),
            IndexModel([("resource_type", ASCENDING), ("action", ASCENDING)], name="idx_audit_resource_action"),
        ])

        # 10. Store Settings Collection Indexes
        await db.settings.create_indexes([
            IndexModel([("key", ASCENDING)], unique=True, name="idx_settings_key_unique"),
        ])

        logger.info("All MongoDB indexes established successfully.")
    except Exception as e:
        logger.warning(f"Notice: MongoDB index creation resulted in: {e}")
