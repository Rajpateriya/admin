from typing import Any, Dict, Optional
from pydantic import Field
from app.models.base import BaseMongoModel


class AuditLog(BaseMongoModel):
    actor_id: str
    actor_email: str
    actor_role: str
    action: str  # e.g., "CREATE_ADMIN", "UPDATE_PRODUCT", "REFUND_ORDER"
    resource_type: str  # e.g., "admin", "product", "order", "category"
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
