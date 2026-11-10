import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_list_admins(client: AsyncClient, superadmin_headers):
    response = await client.get("/api/v1/superadmin/admins", headers=superadmin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_create_admin(client: AsyncClient, superadmin_headers):
    payload = {
        "email": "finance@ecommerce.com",
        "password": "FinancePassword@2026!",
        "full_name": "Finance Officer",
        "role": "FINANCE",
        "phone": "+1 555-0123",
        "custom_permissions": ["analytics:read"],
    }
    response = await client.post("/api/v1/superadmin/admins", json=payload, headers=superadmin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "finance@ecommerce.com"
    assert data["role"] == "FINANCE"


@pytest.mark.asyncio
async def test_create_duplicate_email_fails(client: AsyncClient, superadmin_headers):
    payload = {
        "email": "superadmin@ecommerce.com",
        "password": "SuperAdmin@2026!",
        "full_name": "Duplicate SuperAdmin",
        "role": "SUPERADMIN",
    }
    response = await client.post("/api/v1/superadmin/admins", json=payload, headers=superadmin_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_admin(client: AsyncClient, superadmin_headers, mock_db):
    admin = await mock_db.admins.find_one({"email": "catalog@ecommerce.com"})
    admin_id = str(admin["_id"])

    response = await client.put(
        f"/api/v1/superadmin/admins/{admin_id}",
        json={"full_name": "Senior Catalog Director", "status": "ACTIVE"},
        headers=superadmin_headers,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Senior Catalog Director"


@pytest.mark.asyncio
async def test_force_reset_password_and_token_invalidation(client: AsyncClient, superadmin_headers, mock_db):
    admin = await mock_db.admins.find_one({"email": "catalog@ecommerce.com"})
    admin_id = str(admin["_id"])

    # Old token before password reset
    old_token = create_access_token(
        subject=admin_id,
        role="CATALOG_MANAGER",
        permissions=["products:read"],
        token_version=admin.get("token_version", 1),
    )

    # Force reset password
    reset_res = await client.post(
        f"/api/v1/superadmin/admins/{admin_id}/reset-password",
        json={"new_password": "NewCatalogPassword@2026!"},
        headers=superadmin_headers,
    )
    assert reset_res.status_code == 200

    # Old token must now be rejected
    check_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert check_res.status_code == 401

    # Login with new password works
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "catalog@ecommerce.com", "password": "NewCatalogPassword@2026!"},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_revoke_tokens(client: AsyncClient, superadmin_headers, mock_db):
    admin = await mock_db.admins.find_one({"email": "orders@ecommerce.com"})
    admin_id = str(admin["_id"])

    token = create_access_token(
        subject=admin_id,
        role="ORDER_MANAGER",
        permissions=["orders:read"],
        token_version=admin.get("token_version", 1),
    )

    # Revoke sessions
    revoke_res = await client.post(
        f"/api/v1/superadmin/admins/{admin_id}/revoke-tokens",
        headers=superadmin_headers,
    )
    assert revoke_res.status_code == 200

    # Token should fail now
    check_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert check_res.status_code == 401


@pytest.mark.asyncio
async def test_delete_admin(client: AsyncClient, superadmin_headers, mock_db):
    # Create temp admin
    create_res = await client.post(
        "/api/v1/superadmin/admins",
        json={
            "email": "temp@ecommerce.com",
            "password": "TempPassword@2026!",
            "full_name": "Temporary Admin",
            "role": "CUSTOMER_SUPPORT",
        },
        headers=superadmin_headers,
    )
    temp_id = create_res.json()["id"]

    del_res = await client.delete(f"/api/v1/superadmin/admins/{temp_id}", headers=superadmin_headers)
    assert del_res.status_code == 200

    # Verify deleted
    doc = await mock_db.admins.find_one({"email": "temp@ecommerce.com"})
    assert doc is None


@pytest.mark.asyncio
async def test_prevent_delete_primary_superadmin(client: AsyncClient, superadmin_headers, mock_db):
    root = await mock_db.admins.find_one({"email": "superadmin@ecommerce.com"})
    del_res = await client.delete(f"/api/v1/superadmin/admins/{str(root['_id'])}", headers=superadmin_headers)
    assert del_res.status_code in [400, 403]


@pytest.mark.asyncio
async def test_audit_logs_search_and_export(client: AsyncClient, superadmin_headers):
    # List logs
    list_res = await client.get("/api/v1/superadmin/audit-logs", headers=superadmin_headers)
    assert list_res.status_code == 200
    assert "items" in list_res.json()

    # Export CSV
    export_res = await client.get("/api/v1/superadmin/audit-logs/export", headers=superadmin_headers)
    assert export_res.status_code == 200
    assert export_res.headers["content-type"].startswith("text/csv")
    assert "ID,Timestamp,Actor ID" in export_res.text


@pytest.mark.asyncio
async def test_get_and_update_store_settings(client: AsyncClient, superadmin_headers):
    get_res = await client.get("/api/v1/superadmin/settings", headers=superadmin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["currency_code"] == "USD"

    # Update settings
    put_res = await client.put(
        "/api/v1/superadmin/settings",
        json={"store_name": "Summit Prime Store", "currency_code": "EUR"},
        headers=superadmin_headers,
    )
    assert put_res.status_code == 200
    assert put_res.json()["store_name"] == "Summit Prime Store"
    assert put_res.json()["currency_code"] == "EUR"


@pytest.mark.asyncio
async def test_non_superadmin_forbidden(client: AsyncClient, catalog_headers):
    response = await client.get("/api/v1/superadmin/admins", headers=catalog_headers)
    assert response.status_code == 403
