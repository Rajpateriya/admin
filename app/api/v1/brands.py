from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.schemas.category import BrandCreate, BrandResponse, BrandUpdate
from app.schemas.common import MessageResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/brands", tags=["Brands Management"])


@router.get("", response_model=List[BrandResponse])
async def list_brands(
    is_active: Optional[bool] = Query(None),
    _: Admin = Depends(require_permissions(Permission.BRANDS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all registered product brands."""
    service = CatalogService(db)
    return await service.list_brands(is_active=is_active)


@router.post("", response_model=BrandResponse)
async def create_brand(
    payload: BrandCreate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.BRANDS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a new brand or manufacturer."""
    service = CatalogService(db)
    return await service.create_brand(payload, actor)


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.BRANDS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update brand information, logo, or website."""
    service = CatalogService(db)
    return await service.update_brand(brand_id, payload, actor)


@router.delete("/{brand_id}", response_model=MessageResponse)
async def delete_brand(
    brand_id: str,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.BRANDS_DELETE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a brand."""
    service = CatalogService(db)
    await service.delete_brand(brand_id, actor)
    return MessageResponse(message="Brand deleted successfully.")
