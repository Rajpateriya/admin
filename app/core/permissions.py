from enum import Enum
from typing import Dict, List, Set


class AdminRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    CATALOG_MANAGER = "CATALOG_MANAGER"
    ORDER_MANAGER = "ORDER_MANAGER"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    FINANCE = "FINANCE"


class Permission(str, Enum):
    # Admins management (SuperAdmin only)
    ADMINS_READ = "admins:read"
    ADMINS_WRITE = "admins:write"
    ADMINS_DELETE = "admins:delete"

    # Audit logs
    AUDIT_READ = "audit:read"

    # Store Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Products & Catalog
    PRODUCTS_READ = "products:read"
    PRODUCTS_WRITE = "products:write"
    PRODUCTS_DELETE = "products:delete"

    # Categories
    CATEGORIES_READ = "categories:read"
    CATEGORIES_WRITE = "categories:write"
    CATEGORIES_DELETE = "categories:delete"

    # Brands
    BRANDS_READ = "brands:read"
    BRANDS_WRITE = "brands:write"
    BRANDS_DELETE = "brands:delete"

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"

    # Orders & Fulfillment
    ORDERS_READ = "orders:read"
    ORDERS_WRITE = "orders:write"
    ORDERS_REFUND = "orders:refund"

    # Customers
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_WRITE = "customers:write"

    # Discounts & Coupons
    COUPONS_READ = "coupons:read"
    COUPONS_WRITE = "coupons:write"
    COUPONS_DELETE = "coupons:delete"

    # Analytics & Reports
    ANALYTICS_READ = "analytics:read"


# Default Role-Permission Mapping
ROLE_PERMISSIONS: Dict[AdminRole, Set[str]] = {
    AdminRole.SUPERADMIN: {p.value for p in Permission}.union({"*"}),
    AdminRole.ADMIN: {
        Permission.AUDIT_READ.value,
        Permission.SETTINGS_READ.value,
        Permission.PRODUCTS_READ.value,
        Permission.PRODUCTS_WRITE.value,
        Permission.PRODUCTS_DELETE.value,
        Permission.CATEGORIES_READ.value,
        Permission.CATEGORIES_WRITE.value,
        Permission.CATEGORIES_DELETE.value,
        Permission.BRANDS_READ.value,
        Permission.BRANDS_WRITE.value,
        Permission.BRANDS_DELETE.value,
        Permission.INVENTORY_READ.value,
        Permission.INVENTORY_WRITE.value,
        Permission.ORDERS_READ.value,
        Permission.ORDERS_WRITE.value,
        Permission.ORDERS_REFUND.value,
        Permission.CUSTOMERS_READ.value,
        Permission.CUSTOMERS_WRITE.value,
        Permission.COUPONS_READ.value,
        Permission.COUPONS_WRITE.value,
        Permission.COUPONS_DELETE.value,
        Permission.ANALYTICS_READ.value,
    },
    AdminRole.CATALOG_MANAGER: {
        Permission.PRODUCTS_READ.value,
        Permission.PRODUCTS_WRITE.value,
        Permission.PRODUCTS_DELETE.value,
        Permission.CATEGORIES_READ.value,
        Permission.CATEGORIES_WRITE.value,
        Permission.CATEGORIES_DELETE.value,
        Permission.BRANDS_READ.value,
        Permission.BRANDS_WRITE.value,
        Permission.BRANDS_DELETE.value,
        Permission.INVENTORY_READ.value,
        Permission.INVENTORY_WRITE.value,
        Permission.COUPONS_READ.value,
        Permission.COUPONS_WRITE.value,
        Permission.COUPONS_DELETE.value,
    },
    AdminRole.ORDER_MANAGER: {
        Permission.ORDERS_READ.value,
        Permission.ORDERS_WRITE.value,
        Permission.INVENTORY_READ.value,
        Permission.CUSTOMERS_READ.value,
        Permission.PRODUCTS_READ.value,
    },
    AdminRole.CUSTOMER_SUPPORT: {
        Permission.ORDERS_READ.value,
        Permission.CUSTOMERS_READ.value,
        Permission.CUSTOMERS_WRITE.value,
        Permission.PRODUCTS_READ.value,
        Permission.CATEGORIES_READ.value,
    },
    AdminRole.FINANCE: {
        Permission.ORDERS_READ.value,
        Permission.ORDERS_REFUND.value,
        Permission.ANALYTICS_READ.value,
        Permission.COUPONS_READ.value,
        Permission.COUPONS_WRITE.value,
    },
}


def get_permissions_for_role(role: AdminRole, custom_permissions: List[str] = None) -> Set[str]:
    """Resolve active permissions for an admin combining role permissions and custom overrides."""
    base = set(ROLE_PERMISSIONS.get(role, set()))
    if custom_permissions:
        base.update(custom_permissions)
    return base
