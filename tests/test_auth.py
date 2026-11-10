import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, mock_db):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@ecommerce.com", "password": "SuperAdmin@2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, mock_db):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@ecommerce.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient, mock_db):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@ecommerce.com", "password": "SuperAdmin@2026!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, mock_db):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@ecommerce.com", "password": "SuperAdmin@2026!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_get_my_profile(client: AsyncClient, superadmin_headers):
    response = await client.get("/api/v1/auth/me", headers=superadmin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "superadmin@ecommerce.com"
    assert data["is_superadmin"] is True
    assert "*" in data["permissions"]


@pytest.mark.asyncio
async def test_unauthenticated_request(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_admin_blocked(client: AsyncClient, mock_db):
    await mock_db.admins.update_one(
        {"email": "catalog@ecommerce.com"},
        {"$set": {"status": "INACTIVE"}},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "catalog@ecommerce.com", "password": "CatalogManager@2026!"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_revoked_token_rejected(client: AsyncClient, mock_db):
    admin = await mock_db.admins.find_one({"email": "superadmin@ecommerce.com"})
    # create token with old token_version
    old_token = create_access_token(
        subject=str(admin["_id"]),
        role="SUPERADMIN",
        permissions=["*"],
        token_version=0,
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert response.status_code == 401
    assert "revoked" in response.json()["message"].lower()
