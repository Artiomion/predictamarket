"""Google OAuth — verify id_token from frontend, create/link user, issue JWT."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models.auth import OAuthAccount, RefreshToken, User

from services.auth_service import (
    _create_access_token,
    _create_refresh_token,
    _hash_refresh_token,
)

logger = structlog.get_logger()

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def _verify_google_id_token(id_token: str) -> dict:
    """Verify Google id_token via Google's tokeninfo endpoint.

    Returns dict with: sub, email, email_verified, name, picture.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Option 1: tokeninfo endpoint (simplest, works for id_tokens)
        resp = await client.get(
            GOOGLE_TOKEN_INFO_URL,
            params={"id_token": id_token},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    payload = resp.json()

    # Verify audience matches our client_id
    if settings.GOOGLE_CLIENT_ID and payload.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    if not payload.get("email_verified", "false") == "true":
        raise HTTPException(status_code=401, detail="Google email not verified")

    return {
        "sub": payload["sub"],
        "email": payload["email"].lower().strip(),
        "name": payload.get("name", ""),
        "picture": payload.get("picture"),
    }


async def _verify_google_access_token(access_token: str) -> dict:
    """Alternative: verify via userinfo endpoint when frontend sends access_token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")

    payload = resp.json()
    return {
        "sub": payload["sub"],
        "email": payload["email"].lower().strip(),
        "name": payload.get("name", ""),
        "picture": payload.get("picture"),
    }


async def google_auth(
    session: AsyncSession,
    id_token: str | None = None,
    access_token: str | None = None,
) -> tuple[User, str, str, bool]:
    """Authenticate via Google. Returns (user, access_token, refresh_token, is_new_user).

    Flow:
    1. Verify token with Google
    2. Check if OAuthAccount exists → return existing user
    3. Check if email exists → link OAuth to existing user
    4. Otherwise → create new user + OAuthAccount
    """
    if id_token:
        google_user = await _verify_google_id_token(id_token)
    elif access_token:
        google_user = await _verify_google_access_token(access_token)
    else:
        raise HTTPException(status_code=400, detail="Either id_token or access_token required")

    google_sub = google_user["sub"]
    email = google_user["email"]
    name = google_user["name"]
    picture = google_user.get("picture")

    is_new = False

    # 1. Check existing OAuth link
    oauth_result = await session.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_sub,
        )
    )
    oauth = oauth_result.scalar_one_or_none()

    if oauth:
        # Existing Google user — get their account
        user_result = await session.execute(
            select(User).where(User.id == oauth.user_id, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User account not found")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account deactivated")
    else:
        # 2. Check if email already registered (link OAuth to existing)
        user_result = await session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()

        if user:
            # Link Google to existing email account
            session.add(OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_user_id=google_sub,
            ))
            await logger.ainfo("google_linked", user_id=str(user.id), email=email)
        else:
            # 3. Create new user
            user = User(
                email=email,
                password_hash="oauth:google",  # No password — OAuth only
                full_name=name or email.split("@")[0],
                avatar_url=picture,
                tier="free",
                is_verified=True,  # Google verified the email
            )
            session.add(user)
            await session.flush()

            session.add(OAuthAccount(
                user_id=user.id,
                provider="google",
                provider_user_id=google_sub,
            ))
            is_new = True
            await logger.ainfo("google_registered", user_id=str(user.id), email=email)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    if picture and not user.avatar_url:
        user.avatar_url = picture

    # Issue our JWT tokens
    jwt_access = _create_access_token(user)
    raw_refresh = _create_refresh_token()

    session.add(RefreshToken(
        user_id=user.id,
        token=_hash_refresh_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRATION),
    ))

    await logger.ainfo("google_auth_success", user_id=str(user.id), email=email, is_new=is_new)
    return user, jwt_access, raw_refresh, is_new
