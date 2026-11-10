from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_current_admin
from app.core.database import get_database
from app.models.admin import Admin
from app.schemas.auth import AdminProfileResponse, LoginRequest, RefreshTokenRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Authenticate administrator or SuperAdmin and obtain JWT access & refresh tokens."""
    service = AuthService(db)
    return await service.authenticate_admin(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Refresh expired access token using a valid refresh token."""
    service = AuthService(db)
    return await service.refresh_tokens(payload.refresh_token)


@router.get("/me", response_model=AdminProfileResponse)
async def get_my_profile(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Retrieve profile and active permission scopes of currently logged-in admin."""
    service = AuthService(db)
    return await service.get_admin_profile(str(current_admin.id))
