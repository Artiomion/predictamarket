import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.config import settings
from shared.database import get_read_session, get_session

from schemas.auth import (
    ChangePasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UpdateTierRequest,
    UserResponse,
)
from services.auth_service import (
    change_password,
    get_user_by_id,
    login,
    refresh_tokens,
    register,
    update_profile,
    update_tier,
)

logger = structlog.get_logger()
router = APIRouter()


def _require_internal_key(x_internal_key: str | None = Header(None)) -> str:
    """Verify internal service-to-service API key."""
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: internal endpoint")
    return x_internal_key


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register_endpoint(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user, access_token, refresh_token = await register(
        session, body.email, body.password, body.name
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user, access_token, refresh_token = await login(session, body.email, body.password)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user, access_token, refresh_token = await refresh_tokens(session, body.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> UserResponse:
    user = await get_user_by_id(session, user_id)
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await update_profile(session, user_id, body.name)
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password_endpoint(
    body: ChangePasswordRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    await change_password(session, user_id, body.old_password, body.new_password)
    return MessageResponse(message="Password changed successfully")


@router.put("/tier", response_model=UserResponse)
async def update_tier_endpoint(
    body: UpdateTierRequest,
    _key: str = Depends(_require_internal_key),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Internal endpoint — called by billing service to update user tier."""
    user = await update_tier(session, body.user_id, body.tier)
    return UserResponse.model_validate(user)


@router.post("/google", response_model=TokenResponse)
async def google_auth_endpoint(
    body: GoogleAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate via Google OAuth. Accepts id_token or access_token from frontend."""
    from services.google_oauth import google_auth

    user, access_token, refresh_token, is_new = await google_auth(
        session,
        id_token=body.id_token,
        access_token=body.access_token,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION * 60,
        is_new_user=is_new,
    )
