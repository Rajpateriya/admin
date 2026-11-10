import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import settings
from app.core.database import db_instance, get_database
from app.core.permissions import AdminRole, Permission, get_permissions_for_role
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.admin import Admin, AdminStatus
from app.models.settings import StoreSettings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def mock_db():
    """Create an isolated, in-memory MongoDB database instance using mongomock-motor."""
    client = AsyncMongoMockClient()
    db = client["ecommerce_test_db"]
    db_instance.db = db
    db_instance.client = client

    # Seed default store settings
    default_settings = StoreSettings()
    await db.settings.insert_one(default_settings.to_mongo())

    # Seed root SuperAdmin
    superadmin = Admin(
        email="superadmin@ecommerce.com",
        hashed_password=hash_password("SuperAdmin@2026!"),
        full_name="Root SuperAdmin",
        role=AdminRole.SUPERADMIN,
        status=AdminStatus.ACTIVE,
        is_superadmin=True,
        custom_permissions=["*"],
        token_version=1,
    )
    await db.admins.insert_one(superadmin.to_mongo())

    # Seed Catalog Manager
    cat_admin = Admin(
        email="catalog@ecommerce.com",
        hashed_password=hash_password("CatalogManager@2026!"),
        full_name="Catalog Manager",
        role=AdminRole.CATALOG_MANAGER,
        status=AdminStatus.ACTIVE,
        is_superadmin=False,
        custom_permissions=[],
        token_version=1,
    )
    await db.admins.insert_one(cat_admin.to_mongo())

    # Seed Order Manager
    order_admin = Admin(
        email="orders@ecommerce.com",
        hashed_password=hash_password("OrderManager@2026!"),
        full_name="Order Manager",
        role=AdminRole.ORDER_MANAGER,
        status=AdminStatus.ACTIVE,
        is_superadmin=False,
        custom_permissions=[],
        token_version=1,
    )
    await db.admins.insert_one(order_admin.to_mongo())

    # Override FastAPI dependency
    app.dependency_overrides[get_database] = lambda: db

    yield db

    app.dependency_overrides.clear()
    client.close()


@pytest.fixture
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def superadmin_headers(mock_db) -> Dict[str, str]:
    """Auth header for Root SuperAdmin."""
    admin_doc = await mock_db.admins.find_one({"email": "superadmin@ecommerce.com"})
    token = create_access_token(
        subject=str(admin_doc["_id"]),
        role=AdminRole.SUPERADMIN.value,
        permissions=["*"],
        token_version=admin_doc.get("token_version", 1),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def catalog_headers(mock_db) -> Dict[str, str]:
    """Auth header for Catalog Manager."""
    admin_doc = await mock_db.admins.find_one({"email": "catalog@ecommerce.com"})
    perms = list(get_permissions_for_role(AdminRole.CATALOG_MANAGER))
    token = create_access_token(
        subject=str(admin_doc["_id"]),
        role=AdminRole.CATALOG_MANAGER.value,
        permissions=perms,
        token_version=admin_doc.get("token_version", 1),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def order_headers(mock_db) -> Dict[str, str]:
    """Auth header for Order Manager."""
    admin_doc = await mock_db.admins.find_one({"email": "orders@ecommerce.com"})
    perms = list(get_permissions_for_role(AdminRole.ORDER_MANAGER))
    token = create_access_token(
        subject=str(admin_doc["_id"]),
        role=AdminRole.ORDER_MANAGER.value,
        permissions=perms,
        token_version=admin_doc.get("token_version", 1),
    )
    return {"Authorization": f"Bearer {token}"}
