from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.models.product import ProductStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.product import BulkProductStatusUpdate, ProductCreate, ProductResponse, ProductUpdate
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/products", tags=["Product Catalog Management"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    q: Optional[str] = Query(None, description="Search keyword in title, SKU, tags"),
    category_id: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    status: Optional[ProductStatus] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    is_featured: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: int = Query(-1, description="-1 for DESC, 1 for ASC"),
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List products with full-text search, multi-faceted filtering, and pagination."""
    service = CatalogService(db)
    skip = (page - 1) * limit
    items, total = await service.search_products(
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        status=status,
        min_price=min_price,
        max_price=max_price,
        is_featured=is_featured,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ProductResponse)
async def create_product(
    payload: ProductCreate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new product with optional variants, SKUs, and inventory stock."""
    service = CatalogService(db)
    return await service.create_product(payload, actor)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve detailed product information by ID."""
    service = CatalogService(db)
    return await service.get_product_by_id(product_id)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update product information, pricing, variants, or publishing status."""
    service = CatalogService(db)
    return await service.update_product(product_id, payload, actor)


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: str,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_DELETE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Permanently delete a product from the catalog."""
    service = CatalogService(db)
    await service.delete_product(product_id, actor)
    return MessageResponse(message="Product deleted successfully.")


@router.post("/bulk-status", response_model=MessageResponse)
async def bulk_update_status(
    payload: BulkProductStatusUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.PRODUCTS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Bulk update the status (DRAFT, PUBLISHED, ARCHIVED) for multiple products."""
    service = CatalogService(db)
    modified = await service.bulk_update_status(payload.product_ids, payload.status, actor)
    return MessageResponse(message=f"Successfully updated {modified} product(s) to '{payload.status.value}'.")
