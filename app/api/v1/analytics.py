from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import require_permissions
from app.core.database import get_database
from app.core.permissions import Permission
from app.models.admin import Admin
from app.schemas.analytics import DashboardOverviewResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Business Intelligence"])


@router.get("/dashboard", response_model=DashboardOverviewResponse)
async def get_dashboard_analytics(
    _: Admin = Depends(require_permissions(Permission.ANALYTICS_READ.value)),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Retrieve aggregated executive dashboard metrics:
    Gross revenue, total orders, AOV, order status distributions, 14-day trends, and top products.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_summary()
