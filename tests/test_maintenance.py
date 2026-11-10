import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_maintenance_mode_middleware(client: AsyncClient, superadmin_headers, catalog_headers, mock_db):
    # 1. Initially, maintenance mode is False -> catalog manager can list products
    res1 = await client.get("/api/v1/products", headers=catalog_headers)
    assert res1.status_code == 200

    # 2. Turn on maintenance mode as SuperAdmin
    put_res = await client.put(
        "/api/v1/superadmin/settings",
        json={"maintenance_mode": True},
        headers=superadmin_headers,
    )
    assert put_res.status_code == 200
    assert put_res.json()["maintenance_mode"] is True

    # 3. Non-superadmin is blocked with 503
    res_blocked = await client.get("/api/v1/products", headers=catalog_headers)
    assert res_blocked.status_code == 503
    assert res_blocked.json()["code"] == "MAINTENANCE_MODE"

    # 4. SuperAdmin can still access superadmin endpoints and regular endpoints
    res_super_settings = await client.get("/api/v1/superadmin/settings", headers=superadmin_headers)
    assert res_super_settings.status_code == 200

    res_super_products = await client.get("/api/v1/products", headers=superadmin_headers)
    assert res_super_products.status_code == 200

    # 5. Health endpoint is exempt
    health_res = await client.get("/health")
    assert health_res.status_code == 200

    # 6. Turn off maintenance mode
    off_res = await client.put(
        "/api/v1/superadmin/settings",
        json={"maintenance_mode": False},
        headers=superadmin_headers,
    )
    assert off_res.status_code == 200

    # 7. Non-superadmin is restored
    res_restored = await client.get("/api/v1/products", headers=catalog_headers)
    assert res_restored.status_code == 200
