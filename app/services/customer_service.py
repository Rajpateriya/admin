from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.customer import Customer, CustomerStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreateRequest, CustomerResponse, CustomerUpdateRequest


class CustomerService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.audit_repo = AuditRepository(db)

    async def create_customer(
        self,
        data: CustomerCreateRequest,
        actor: Dict[str, Any],
    ) -> CustomerResponse:
        existing = await self.customer_repo.get_by_email(data.email)
        if existing:
            raise ConflictException(f"Customer with email '{data.email}' already exists.")

        customer = Customer(
            email=data.email.lower(),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            addresses=data.addresses,
            tags=data.tags,
            status=CustomerStatus.ACTIVE,
        )
        created = await self.customer_repo.create(customer)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="CREATE_CUSTOMER",
            resource_type="customer",
            resource_id=str(created.id),
            details={"email": created.email, "name": f"{created.first_name} {created.last_name}"},
        )
        return CustomerResponse(**created.model_dump(by_alias=False))

    async def update_customer(
        self,
        customer_id: str,
        data: CustomerUpdateRequest,
        actor: Dict[str, Any],
    ) -> CustomerResponse:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)

        patch = data.model_dump(exclude_unset=True)
        if "addresses" in patch and patch["addresses"] is not None:
            patch["addresses"] = [a if isinstance(a, dict) else a.model_dump() for a in patch["addresses"]]

        updated = await self.customer_repo.update(customer_id, patch)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_CUSTOMER",
            resource_type="customer",
            resource_id=customer_id,
            details=patch,
        )
        return CustomerResponse(**updated.model_dump(by_alias=False))

    async def delete_customer(
        self,
        customer_id: str,
        actor: Dict[str, Any],
    ) -> None:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)

        has_orders = await self.db.orders.count_documents({"customer_id": customer_id})
        if has_orders > 0:
            raise BadRequestException("Cannot delete customer with existing order history. Consider suspending the customer instead.")

        await self.customer_repo.delete(customer_id)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="DELETE_CUSTOMER",
            resource_type="customer",
            resource_id=customer_id,
            details={"email": customer.email},
        )

    async def list_customers(
        self,
        q: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        min_spent: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[CustomerResponse], int]:
        customers, total = await self.customer_repo.filter_customers(
            q=q,
            status=status,
            min_spent=min_spent,
            skip=skip,
            limit=limit,
        )
        responses = [CustomerResponse(**c.model_dump(by_alias=False)) for c in customers]
        return responses, total

    async def get_customer_by_id(self, customer_id: str) -> CustomerResponse:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)
        return CustomerResponse(**customer.model_dump(by_alias=False))

    async def update_status(
        self,
        customer_id: str,
        status: CustomerStatus,
        actor: Dict[str, Any],
    ) -> CustomerResponse:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)

        updated = await self.customer_repo.update(customer_id, {"status": status.value})

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="UPDATE_CUSTOMER_STATUS",
            resource_type="customer",
            resource_id=customer_id,
            details={"email": customer.email, "previous_status": customer.status.value, "new_status": status.value},
        )
        return CustomerResponse(**updated.model_dump(by_alias=False))

    async def add_internal_note(
        self,
        customer_id: str,
        note: str,
        actor: Dict[str, Any],
    ) -> CustomerResponse:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)

        formatted_note = f"[{actor['email']}]: {note}"
        updated = await self.customer_repo.add_note(customer_id, formatted_note)

        await self.audit_repo.log_action(
            actor_id=actor["id"],
            actor_email=actor["email"],
            actor_role=actor["role"],
            action="ADD_CUSTOMER_NOTE",
            resource_type="customer",
            resource_id=customer_id,
            details={"email": customer.email, "note": note},
        )
        return CustomerResponse(**updated.model_dump(by_alias=False))
