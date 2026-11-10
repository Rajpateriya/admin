from fastapi import APIRouter
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.brands import router as brands_router
from app.api.v1.categories import router as categories_router
from app.api.v1.coupons import router as coupons_router
from app.api.v1.customers import router as customers_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.superadmin import router as superadmin_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(superadmin_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(brands_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(coupons_router)
api_v1_router.include_router(analytics_router)
