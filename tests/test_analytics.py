from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_dashboard_overview(client: AsyncClient, superadmin_headers, catalog_headers, mock_db):
    now = datetime.now(timezone.utc)

    # 1. Seed demo orders into mock_db
    order_doc1 = {
        "order_number": "ORD-TEST-001",
        "customer_id": "cust1",
        "customer_email": "c1@test.com",
        "customer_name": "Customer One",
        "status": "DELIVERED",
        "payment_status": "PAID",
        "subtotal": 200.0,
        "discount_amount": 0.0,
        "tax_amount": 10.0,
        "shipping_amount": 10.0,
        "total_amount": 220.0,
        "items": [
            {
                "product_id": "prod_1",
                "title": "Ultra Gaming Laptop",
                "sku": "LAP-01",
                "quantity": 1,
                "unit_price": 200.0,
                "total_price": 200.0,
            }
        ],
        "created_at": now - timedelta(days=2),
    }

    order_doc2 = {
        "order_number": "ORD-TEST-002",
        "customer_id": "cust2",
        "customer_email": "c2@test.com",
        "customer_name": "Customer Two",
        "status": "PENDING",
        "payment_status": "PAID",
        "subtotal": 100.0,
        "discount_amount": 10.0,
        "tax_amount": 5.0,
        "shipping_amount": 5.0,
        "total_amount": 100.0,
        "items": [
            {
                "product_id": "prod_1",
                "title": "Ultra Gaming Laptop",
                "sku": "LAP-01",
                "quantity": 1,
                "unit_price": 100.0,
                "total_price": 100.0,
            }
        ],
        "created_at": now - timedelta(days=1),
    }

    await mock_db.orders.insert_many([order_doc1, order_doc2])

    # 2. Call Analytics endpoint as SuperAdmin
    res = await client.get("/api/v1/analytics/dashboard", headers=superadmin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_revenue"] == 320.0  # 220 + 100
    assert data["total_orders"] >= 2
    assert data["average_order_value"] > 0
    assert data["pending_orders_count"] >= 1

    # Check top products aggregation
    assert len(data["top_selling_products"]) >= 1
    assert data["top_selling_products"][0]["sku"] == "LAP-01"
    assert data["top_selling_products"][0]["units_sold"] == 2

    # Check sales trend
    assert len(data["recent_sales_trend"]) >= 1

    # 3. Check permission enforcement: Catalog Manager does not have analytics:read
    forbidden_res = await client.get("/api/v1/analytics/dashboard", headers=catalog_headers)
    assert forbidden_res.status_code == 403
