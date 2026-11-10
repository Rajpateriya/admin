import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_order_creation_and_lifecycle(client: AsyncClient, order_headers, catalog_headers, superadmin_headers):
    # 1. Create a product with 50 units
    prod_res = await client.post(
        "/api/v1/products",
        json={
            "title": "Ergonomic Office Chair",
            "sku": "CHAIR-ERGO-01",
            "description": "Adjustable lumbar mesh chair",
            "base_price": 250.0,
            "stock_quantity": 50,
            "status": "PUBLISHED",
        },
        headers=catalog_headers,
    )
    product_id = prod_res.json()["id"]

    # 2. Create customer
    cust_res = await client.post(
        "/api/v1/customers",
        json={
            "email": "sarah.connor@example.com",
            "first_name": "Sarah",
            "last_name": "Connor",
            "phone": "+1 310-555-0100",
            "addresses": [
                {
                    "first_name": "Sarah",
                    "last_name": "Connor",
                    "address_line1": "450 Bunker Way",
                    "city": "Los Angeles",
                    "state": "CA",
                    "postal_code": "90001",
                    "country": "US",
                    "is_default": True,
                }
            ],
        },
        headers=superadmin_headers,
    )
    assert cust_res.status_code == 200
    cust_id = cust_res.json()["id"]

    # 3. Create an order for 2 chairs
    order_payload = {
        "customer_id": cust_id,
        "customer_email": "sarah.connor@example.com",
        "customer_name": "Sarah Connor",
        "items": [{"product_id": product_id, "quantity": 2, "unit_price": 250.0}],
        "shipping_address": {
            "first_name": "Sarah",
            "last_name": "Connor",
            "address_line1": "450 Bunker Way",
            "city": "Los Angeles",
            "state": "CA",
            "postal_code": "90001",
            "country": "US",
        },
        "tax_amount": 35.0,
        "shipping_amount": 15.0,
        "notes": "Gate code #1984",
    }
    order_res = await client.post("/api/v1/orders", json=order_payload, headers=order_headers)
    assert order_res.status_code == 200
    order_data = order_res.json()
    order_id = order_data["id"]
    assert order_data["subtotal"] == 500.0
    assert order_data["total_amount"] == 550.0  # 500 + 35 + 15
    assert order_data["status"] == "PENDING"

    # Verify inventory was reduced from 50 to 48
    prod_check = await client.get(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert prod_check.json()["stock_quantity"] == 48

    # 4. State Transition: PENDING -> CONFIRMED
    conf_res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CONFIRMED"},
        headers=order_headers,
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "CONFIRMED"

    # 5. State Transition: CONFIRMED -> PROCESSING
    proc_res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "PROCESSING"},
        headers=order_headers,
    )
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == "PROCESSING"

    # 6. Illegal Transition: PROCESSING -> DELIVERED (Must be rejected!)
    illegal_res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "DELIVERED"},
        headers=order_headers,
    )
    assert illegal_res.status_code == 400
    assert "invalid order status transition" in illegal_res.json()["message"].lower()

    # 7. Update Tracking (auto-advances PROCESSING -> SHIPPED)
    track_res = await client.patch(
        f"/api/v1/orders/{order_id}/tracking",
        json={"carrier": "UPS", "tracking_number": "1Z9999999999999999", "tracking_url": "https://ups.com/track"},
        headers=order_headers,
    )
    assert track_res.status_code == 200
    assert track_res.json()["status"] == "SHIPPED"
    assert track_res.json()["shipping_info"]["carrier"] == "UPS"

    # 8. State Transition: SHIPPED -> DELIVERED
    deliv_res = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "DELIVERED"},
        headers=order_headers,
    )
    assert deliv_res.status_code == 200
    assert deliv_res.json()["status"] == "DELIVERED"

    # 9. Add internal staff note
    note_res = await client.post(
        f"/api/v1/orders/{order_id}/notes",
        json={"note": "Customer called confirming delivery on porch."},
        headers=order_headers,
    )
    assert note_res.status_code == 200
    assert len(note_res.json()["admin_notes"]) >= 2

    # 10. Issue Full Refund with restock
    refund_res = await client.post(
        f"/api/v1/orders/{order_id}/refund",
        json={"amount": 550.0, "reason": "Defective parts reported", "restock_inventory": True},
        headers=superadmin_headers,
    )
    assert refund_res.status_code == 200
    assert refund_res.json()["status"] == "REFUNDED"
    assert refund_res.json()["payment_status"] == "REFUNDED"

    # Verify inventory was restocked back to 50
    prod_restock = await client.get(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert prod_restock.json()["stock_quantity"] == 50


@pytest.mark.asyncio
async def test_order_cancellation_and_restock(client: AsyncClient, order_headers, catalog_headers):
    # Create product with 10 units
    prod_res = await client.post(
        "/api/v1/products",
        json={
            "title": "Wireless Earbuds",
            "sku": "EARBUD-WL-01",
            "description": "BT 5.3 earbuds",
            "base_price": 50.0,
            "stock_quantity": 10,
            "status": "PUBLISHED",
        },
        headers=catalog_headers,
    )
    product_id = prod_res.json()["id"]

    # Create order for 3 units (leaving 7 in stock)
    order_res = await client.post(
        "/api/v1/orders",
        json={
            "customer_email": "john.test@example.com",
            "customer_name": "John Test",
            "items": [{"product_id": product_id, "quantity": 3}],
            "shipping_address": {
                "first_name": "John",
                "last_name": "Test",
                "address_line1": "10 Pine St",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "US",
            },
        },
        headers=order_headers,
    )
    order_id = order_res.json()["id"]

    # Verify stock is now 7
    prod_mid = await client.get(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert prod_mid.json()["stock_quantity"] == 7

    # Cancel order with restock
    cancel_res = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"reason": "Customer changed mind before processing", "restock_inventory": True},
        headers=order_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
    assert cancel_res.json()["cancellation_reason"] == "Customer changed mind before processing"

    # Verify stock returned to 10
    prod_end = await client.get(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert prod_end.json()["stock_quantity"] == 10
