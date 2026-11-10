from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import MessageResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/categories", tags=["Categories Management"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    is_active: Optional[bool] = Query(None),
    _: Admin = Depends(require_permissions(Permission.CATEGORIES_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all categories with optional active status filter."""
    service = CatalogService(db)
    return await service.list_categories(is_active=is_active)


@router.get("/tree", response_model=List[Dict[str, Any]])
async def get_category_tree(
    _: Admin = Depends(require_permissions(Permission.CATEGORIES_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve full hierarchical parent-child category tree for menu/catalog structuring."""
    service = CatalogService(db)
    return await service.get_category_tree()


@router.post("", response_model=CategoryResponse)
async def create_category(
    payload: CategoryCreate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CATEGORIES_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new category (top-level or child under parent_id)."""
    service = CatalogService(db)
    return await service.create_category(payload, actor)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CATEGORIES_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update category details, parent hierarchy, or active status."""
    service = CatalogService(db)
    return await service.update_category(category_id, payload, actor)


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: str,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CATEGORIES_DELETE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a category (prevented if subcategories or products are linked)."""
    service = CatalogService(db)
    await service.delete_category(category_id, actor)
    return MessageResponse(message="Category deleted successfully.")
