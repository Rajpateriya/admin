import logging
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.permissions import AdminRole
from app.core.security import hash_password
from app.models.admin import Admin, AdminStatus
from app.models.brand import Brand
from app.models.category import Category
from app.models.coupon import Coupon, DiscountType
from app.models.customer import Address, Customer, CustomerStatus
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, ShippingInfo
from app.models.product import Product, ProductStatus, ProductVariant
from app.models.settings import StoreSettings
from app.repositories.admin_repository import AdminRepository

logger = logging.getLogger("uvicorn.error")


async def seed_initial_superadmin(db: AsyncIOMotorDatabase):
    """Ensure the root SuperAdmin exists on initial startup."""
    admin_repo = AdminRepository(db)
    existing = await admin_repo.get_by_email(settings.SUPERADMIN_EMAIL)
    if not existing:
        logger.info(f"Seeding initial SuperAdmin account: {settings.SUPERADMIN_EMAIL}...")
        superadmin = Admin(
            email=settings.SUPERADMIN_EMAIL.lower(),
            hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
            full_name=settings.SUPERADMIN_FULL_NAME,
            role=AdminRole.SUPERADMIN,
            status=AdminStatus.ACTIVE,
            is_superadmin=True,
            custom_permissions=["*"],
        )
        await admin_repo.create(superadmin)
        logger.info("Root SuperAdmin seeded successfully.")
    else:
        logger.info("SuperAdmin already exists.")


async def seed_demo_store_data(db: AsyncIOMotorDatabase):
    """Seed sample catalog, customers, coupons, and orders for testing."""
    # Ensure default store settings
    settings_count = await db.settings.count_documents({})
    if settings_count == 0:
        default_settings = StoreSettings()
        await db.settings.insert_one(default_settings.to_mongo())

    # Check if products already exist
    products_count = await db.products.count_documents({})
    if products_count > 0:
        return

    logger.info("Seeding demo e-commerce store data...")

    # 1. Categories
    cat_electronics = Category(name="Electronics", slug="electronics", description="Gadgets and electronics")
    cat_apparel = Category(name="Apparel & Fashion", slug="apparel", description="Clothing and wear")
    cat_audio = Category(name="Audio & Headphones", slug="audio", description="High fidelity audio")

    await db.categories.insert_one(cat_electronics.to_mongo())
    await db.categories.insert_one(cat_apparel.to_mongo())
    cat_audio.parent_id = str(cat_electronics.id)
    await db.categories.insert_one(cat_audio.to_mongo())

    # 2. Brands
    brand_sony = Brand(name="Sony", slug="sony", description="Sony Electronics")
    brand_apple = Brand(name="Apple", slug="apple", description="Apple Inc.")
    brand_nike = Brand(name="Nike", slug="nike", description="Nike Athletic")
    await db.brands.insert_one(brand_sony.to_mongo())
    await db.brands.insert_one(brand_apple.to_mongo())
    await db.brands.insert_one(brand_nike.to_mongo())

    # 3. Products
    p1 = Product(
        title="Sony WH-1000XM5 Wireless Headphones",
        slug="sony-wh-1000xm5",
        description="Industry-leading noise cancelling with two processors and 8 microphones.",
        short_description="Flagship ANC headphones",
        status=ProductStatus.PUBLISHED,
        sku="SONY-WH1000XM5-BLK",
        base_price=399.99,
        compare_at_price=449.99,
        cost_price=240.00,
        stock_quantity=45,
        low_stock_threshold=10,
        category_id=str(cat_audio.id),
        brand_id=str(brand_sony.id),
        tags=["audio", "headphones", "anc", "wireless"],
        images=["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800"],
        variants=[
            ProductVariant(
                id="var_sony_blk",
                title="Black",
                sku="SONY-XM5-BLK",
                price=399.99,
                stock_quantity=30,
                attributes={"color": "Black"},
            ),
            ProductVariant(
                id="var_sony_slv",
                title="Silver",
                sku="SONY-XM5-SLV",
                price=399.99,
                stock_quantity=15,
                attributes={"color": "Silver"},
            ),
        ],
        is_featured=True,
    )

    p2 = Product(
        title="Nike Air Zoom Pegasus 40",
        slug="nike-air-zoom-pegasus-40",
        description="A springy ride for every run, familiar feel return to help you accomplish your goals.",
        status=ProductStatus.PUBLISHED,
        sku="NIKE-PEG40-ALL",
        base_price=139.99,
        stock_quantity=4,  # Intentionally low to test low stock alerts!
        low_stock_threshold=8,
        category_id=str(cat_apparel.id),
        brand_id=str(brand_nike.id),
        tags=["running", "shoes", "nike"],
        variants=[
            ProductVariant(
                id="var_nike_us10",
                title="Size 10 - Blue",
                sku="NIKE-PEG40-BLU-10",
                price=139.99,
                stock_quantity=2,
                attributes={"size": "US 10", "color": "Blue"},
            ),
            ProductVariant(
                id="var_nike_us11",
                title="Size 11 - Blue",
                sku="NIKE-PEG40-BLU-11",
                price=139.99,
                stock_quantity=2,
                attributes={"size": "US 11", "color": "Blue"},
            ),
        ],
    )
    await db.products.insert_one(p1.to_mongo())
    await db.products.insert_one(p2.to_mongo())

    # 4. Customers
    cust_addr = Address(
        first_name="Jane",
        last_name="Doe",
        address_line1="123 Market Street",
        city="San Francisco",
        state="CA",
        postal_code="94105",
        country="US",
        phone="+1 415-555-0199",
        is_default=True,
    )
    cust1 = Customer(
        email="jane.doe@example.com",
        first_name="Jane",
        last_name="Doe",
        phone="+1 415-555-0199",
        status=CustomerStatus.ACTIVE,
        addresses=[cust_addr],
        orders_count=1,
        total_spent=399.99,
        last_order_at=datetime.now(timezone.utc),
        tags=["VIP"],
    )
    await db.customers.insert_one(cust1.to_mongo())

    # 5. Coupon
    coupon = Coupon(
        code="WELCOME20",
        discount_type=DiscountType.PERCENTAGE,
        value=20.0,
        min_order_amount=50.0,
        usage_limit=1000,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_to=datetime.now(timezone.utc) + timedelta(days=90),
        is_active=True,
    )
    await db.coupons.insert_one(coupon.to_mongo())

    # 6. Orders
    order1 = Order(
        order_number="ORD-202611-0001",
        customer_id=str(cust1.id),
        customer_email=cust1.email,
        customer_name=f"{cust1.first_name} {cust1.last_name}",
        items=[
            OrderItem(
                product_id=str(p1.id),
                variant_id="var_sony_blk",
                title=p1.title,
                sku="SONY-XM5-BLK",
                quantity=1,
                unit_price=399.99,
                total_price=399.99,
            )
        ],
        shipping_address=cust_addr,
        billing_address=cust_addr,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID,
        payment_method="STRIPE_CARD",
        subtotal=399.99,
        discount_amount=0.0,
        tax_amount=28.00,
        shipping_amount=0.0,
        total_amount=427.99,
        shipping_info=ShippingInfo(
            carrier="FedEx Express",
            tracking_number="FDX9283749283",
            tracking_url="https://fedex.com/track/FDX9283749283",
            shipped_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    )
    await db.orders.insert_one(order1.to_mongo())

    logger.info("Demo e-commerce data seeded successfully.")


async def main():
    import argparse
    from app.core.database import close_mongo_connection, connect_to_mongo, db_instance
    from app.core.indexes import create_indexes

    parser = argparse.ArgumentParser(description="E-Commerce Admin Database Seeder CLI")
    parser.add_argument("--superadmin-only", action="store_true", help="Seed only root SuperAdmin account")
    parser.add_argument("--demo-only", action="store_true", help="Seed only demo store data")
    args = parser.parse_args()

    print("Connecting to MongoDB...")
    await connect_to_mongo()
    if db_instance.db is not None:
        print("Ensuring indexes...")
        await create_indexes(db_instance.db)

        if not args.demo_only:
            print("Seeding root SuperAdmin...")
            await seed_initial_superadmin(db_instance.db)

        if not args.superadmin_only:
            print("Seeding demo e-commerce store catalog, customers, and orders...")
            await seed_demo_store_data(db_instance.db)

    await close_mongo_connection()
    print("Seeding operation finished successfully.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
