import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_inventory_adjustments_and_alerts(client: AsyncClient, catalog_headers, superadmin_headers):
    # 1. Create a product with 10 units and low stock threshold 8
    prod_res = await client.post(
        "/api/v1/products",
        json={
            "title": "Mechanical Keyboard Pro",
            "sku": "KB-PRO-100",
            "description": "RGB mechanical keyboard",
            "base_price": 129.99,
            "stock_quantity": 10,
            "low_stock_threshold": 8,
            "status": "PUBLISHED",
        },
        headers=catalog_headers,
    )
    assert prod_res.status_code == 200
    product_id = prod_res.json()["id"]

    # 2. Add stock (+15) via PURCHASE_RECEIPT
    add_res = await client.post(
        "/api/v1/inventory/adjust",
        json={
            "product_id": product_id,
            "quantity_delta": 15,
            "reason": "PURCHASE_RECEIPT",
            "notes": "PO-9912 Shipment received",
        },
        headers=superadmin_headers,
    )
    assert add_res.status_code == 200
    data = add_res.json()
    assert data["previous_stock"] == 10
    assert data["new_stock"] == 25
    assert data["quantity_delta"] == 15

    # 3. Deduct stock (-20) via MANUAL_CORRECTION
    sub_res = await client.post(
        "/api/v1/inventory/adjust",
        json={
            "product_id": product_id,
            "quantity_delta": -20,
            "reason": "MANUAL_CORRECTION",
            "notes": "Inventory count correction",
        },
        headers=superadmin_headers,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["new_stock"] == 5

    # 4. Reject reduction exceeding available stock (-10 when only 5 exist)
    fail_res = await client.post(
        "/api/v1/inventory/adjust",
        json={
            "product_id": product_id,
            "quantity_delta": -10,
            "reason": "DAMAGED",
        },
        headers=superadmin_headers,
    )
    assert fail_res.status_code == 400
    assert "insufficient stock" in fail_res.json()["message"].lower()

    # 5. Low stock alerts (stock is 5, threshold is 8 -> should be in alerts!)
    alert_res = await client.get("/api/v1/inventory/alerts/low-stock", headers=superadmin_headers)
    assert alert_res.status_code == 200
    alerts = alert_res.json()
    assert any(a["product_id"] == product_id for a in alerts)

    # 6. Movement history filtering
    history_res = await client.get(
        f"/api/v1/inventory/history?product_id={product_id}&reason=PURCHASE_RECEIPT",
        headers=superadmin_headers,
    )
    assert history_res.status_code == 200
    h_data = history_res.json()
    assert h_data["total"] >= 1
    assert h_data["items"][0]["reason"] == "PURCHASE_RECEIPT"
