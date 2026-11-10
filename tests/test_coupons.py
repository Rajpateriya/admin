from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_coupon_crud_and_validation_engine(client: AsyncClient, catalog_headers, superadmin_headers):
    now = datetime.now(timezone.utc)

    # 1. Create a 20% coupon with min order $100 and max discount $30
    coupon_payload = {
        "code": "SUMMER20",
        "discount_type": "PERCENTAGE",
        "value": 20.0,
        "min_order_amount": 100.0,
        "max_discount_amount": 30.0,
        "usage_limit": 50,
        "per_customer_limit": 1,
        "valid_from": (now - timedelta(days=1)).isoformat(),
        "valid_to": (now + timedelta(days=30)).isoformat(),
        "is_active": True,
    }
    create_res = await client.post("/api/v1/coupons", json=coupon_payload, headers=catalog_headers)
    assert create_res.status_code == 200
    coupon_data = create_res.json()
    coupon_id = coupon_data["id"]
    assert coupon_data["code"] == "SUMMER20"

    # 2. Duplicate coupon code conflict
    dup_res = await client.post("/api/v1/coupons", json=coupon_payload, headers=catalog_headers)
    assert dup_res.status_code == 409

    # 3. Validate coupon: Below minimum spend ($80 < $100) -> should fail
    val_fail_spend = await client.post(
        "/api/v1/coupons/validate",
        json={"code": "SUMMER20", "order_subtotal": 80.0},
        headers=catalog_headers,
    )
    assert val_fail_spend.status_code == 200
    assert val_fail_spend.json()["valid"] is False
    assert "minimum order spend" in val_fail_spend.json()["message"].lower()

    # 4. Validate coupon: Valid order ($200) -> 20% of 200 is 40, capped at max_discount 30
    val_success = await client.post(
        "/api/v1/coupons/validate",
        json={"code": "SUMMER20", "order_subtotal": 200.0},
        headers=catalog_headers,
    )
    assert val_success.status_code == 200
    val_data = val_success.json()
    assert val_data["valid"] is True
    assert val_data["discount_amount"] == 30.0
    assert val_data["final_total"] == 170.0

    # 5. Fixed amount coupon
    fixed_payload = {
        "code": "FLAT15OFF",
        "discount_type": "FIXED_AMOUNT",
        "value": 15.0,
        "valid_to": (now + timedelta(days=10)).isoformat(),
        "is_active": True,
    }
    await client.post("/api/v1/coupons", json=fixed_payload, headers=catalog_headers)

    val_fixed = await client.post(
        "/api/v1/coupons/validate",
        json={"code": "FLAT15OFF", "order_subtotal": 60.0},
        headers=catalog_headers,
    )
    assert val_fixed.status_code == 200
    assert val_fixed.json()["valid"] is True
    assert val_fixed.json()["discount_amount"] == 15.0
    assert val_fixed.json()["final_total"] == 45.0

    # 6. Check coupon stats endpoint
    stats_res = await client.get(f"/api/v1/coupons/{coupon_id}/stats", headers=catalog_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["code"] == "SUMMER20"
    assert "total_discount_given" in stats_res.json()

    # 7. Update coupon (deactivate)
    put_res = await client.put(f"/api/v1/coupons/{coupon_id}", json={"is_active": False}, headers=catalog_headers)
    assert put_res.status_code == 200

    # Validate inactive coupon
    val_inactive = await client.post(
        "/api/v1/coupons/validate",
        json={"code": "SUMMER20", "order_subtotal": 150.0},
        headers=catalog_headers,
    )
    assert val_inactive.json()["valid"] is False
    assert "inactive" in val_inactive.json()["message"].lower()

    # 8. Delete coupon
    del_res = await client.delete(f"/api/v1/coupons/{coupon_id}", headers=catalog_headers)
    assert del_res.status_code == 200
