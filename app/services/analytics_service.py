from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import DashboardOverviewResponse


class AnalyticsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.analytics_repo = AnalyticsRepository(db)

    async def get_dashboard_summary(self) -> DashboardOverviewResponse:
        return await self.analytics_repo.get_dashboard_overview()
