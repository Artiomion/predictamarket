from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class UpdateProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class UpdateTierRequest(BaseModel):
    user_id: UUID
    tier: str = Field(..., pattern="^(free|pro|premium)$")


class GoogleAuthRequest(BaseModel):
    id_token: str | None = None
    access_token: str | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool = False


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    tier: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
