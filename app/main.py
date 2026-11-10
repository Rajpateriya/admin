import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo, db_instance
from app.core.exceptions import AppException
from app.core.indexes import create_indexes
from app.utils.seed import seed_demo_store_data, seed_initial_superadmin

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # 1. Startup: Connect to MongoDB
    await connect_to_mongo()
    if db_instance.db is not None:
        # 2. Ensure indexes
        await create_indexes(db_instance.db)
        # 3. Seed Root SuperAdmin
        await seed_initial_superadmin(db_instance.db)
        # 4. Seed demo data in development mode
        if settings.APP_ENV in ["development", "dev", "test"]:
            await seed_demo_store_data(db_instance.db)

    yield

    # Shutdown: Close MongoDB connection pool
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
# E-Commerce Admin & SuperAdmin Platform API

A robust, enterprise-grade, asynchronous backend service built with **FastAPI** and **MongoDB**.

### Core Architecture:
- **SuperAdmin Platform Governance**: Manage admin users, assign granular roles & permission scopes, audit logs surveillance, and global store configuration.
- **Product & Catalog Management**: Multi-level categories hierarchy, brand registry, products with dynamic variants, attributes, SKUs, and stock tracking.
- **Inventory & Warehouse Tracking**: Atomic stock movements with reason codes, audit trail, and low-stock alerts.
- **Order Pipeline & Fulfillment**: Strict state-machine transitions, carrier tracking updates, customer address management, and refunds with inventory restock.
- **Customer CRM & Intelligence**: Customer lifetime spend metrics, account moderation (suspend/flag), and internal staff notes.
- **Promotions & Coupons**: Flexible discount logic (percentage, fixed amount, free shipping), spend rules, and usage caps.
- **Executive Analytics**: Real-time sales trends, order status distributions, AOV, and top-performing products.
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ----------------- MIDDLEWARE CONFIGURATION -----------------
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    """Add execution time header and unique request tracking ID."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def check_maintenance_mode(request: Request, call_next):
    """Enforce maintenance mode when active: restrict store operations to SuperAdmins only."""
    path = request.url.path
    exempt_prefixes = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        f"{settings.API_V1_STR}/auth",
        f"{settings.API_V1_STR}/superadmin",
    ]
    if any(path.startswith(prefix) for prefix in exempt_prefixes) or not path.startswith(settings.API_V1_STR):
        return await call_next(request)

    if db_instance.db is not None:
        try:
            settings_doc = await db_instance.db.settings.find_one({"key": "global_store_settings"})
            if settings_doc and settings_doc.get("maintenance_mode", False):
                auth_header = request.headers.get("Authorization")
                is_super = False
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        from app.core.security import decode_token
                        payload = decode_token(token)
                        if payload.get("role") == "SUPERADMIN" or "*" in payload.get("permissions", []):
                            is_super = True
                    except Exception:
                        pass

                if not is_super:
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "success": False,
                            "code": "MAINTENANCE_MODE",
                            "message": "The platform is currently undergoing scheduled maintenance. Store operations are paused.",
                            "request_id": getattr(request.state, "request_id", None),
                        },
                    )
        except Exception:
            pass

    return await call_next(request)


# ----------------- GLOBAL EXCEPTION HANDLERS -----------------
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.code,
            "message": exc.detail,
            "extra": exc.extra,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", [])])
        errors.append({"field": loc, "message": err.get("msg")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "code": "VALIDATION_ERROR",
            "message": "Input validation failed.",
            "errors": errors,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception during request processing: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact system support.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ----------------- HEALTH & SYSTEM CHECKS -----------------
@app.get("/health", tags=["Health & Status"])
async def health_check():
    """Verify application health and database connectivity."""
    db_status = "disconnected"
    if db_instance.db is not None:
        try:
            await db_instance.db.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "unresponsive"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "environment": settings.APP_ENV,
        "timestamp": time.time(),
    }


# Mount V1 Routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
