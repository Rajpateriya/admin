from typing import Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin_actor, require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.models.customer import CustomerStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerNoteCreateRequest,
    CustomerResponse,
    CustomerStatusUpdateRequest,
    CustomerUpdateRequest,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customer Intelligence & Moderation"])


@router.post("", response_model=CustomerResponse)
async def create_customer(
    payload: CustomerCreateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a new customer account with addresses and tags."""
    service = CustomerService(db)
    return await service.create_customer(payload, actor)


@router.get("", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    q: Optional[str] = Query(None, description="Search by email, first name, last name"),
    status: Optional[CustomerStatus] = Query(None),
    min_spent: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List registered customers with lifetime spend metrics, order counts, and search filters."""
    service = CustomerService(db)
    skip = (page - 1) * limit
    customers, total = await service.list_customers(
        q=q,
        status=status,
        min_spent=min_spent,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse.create(items=customers, total=total, page=page, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve complete customer profile, saved addresses, and internal moderation notes."""
    service = CustomerService(db)
    return await service.get_customer_by_id(customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    payload: CustomerUpdateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update customer demographic details, contact info, tags, or addresses."""
    service = CustomerService(db)
    return await service.update_customer(customer_id, payload, actor)


@router.delete("/{customer_id}", response_model=MessageResponse)
async def delete_customer(
    customer_id: str,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a customer record (only allowed if customer has no order history)."""
    service = CustomerService(db)
    await service.delete_customer(customer_id, actor)
    return MessageResponse(message="Customer deleted successfully.")


@router.patch("/{customer_id}/status", response_model=CustomerResponse)
async def update_customer_status(
    customer_id: str,
    payload: CustomerStatusUpdateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Moderate customer account status (ACTIVE, SUSPENDED, FLAGGED for fraud)."""
    service = CustomerService(db)
    return await service.update_status(customer_id, payload.status, actor)


@router.post("/{customer_id}/notes", response_model=CustomerResponse)
async def add_customer_note(
    customer_id: str,
    payload: CustomerNoteCreateRequest,
    actor: dict = Depends(get_current_admin_actor),
    _: Admin = Depends(require_permissions(Permission.CUSTOMERS_WRITE.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Append an internal CRM note to a customer's record."""
    service = CustomerService(db)
    return await service.add_internal_note(customer_id, payload.note, actor)
