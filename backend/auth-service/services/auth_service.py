import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models.auth import RefreshToken, User

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# bcrypt is CPU-bound — run in thread pool to avoid blocking event loop
async def _hash_password(password: str) -> str:
    return await asyncio.to_thread(pwd_context.hash, password)


async def _verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(pwd_context.verify, plain, hashed)


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tier": user.tier,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRATION),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token() -> str:
    """Generate a cryptographically secure refresh token."""
    return secrets.token_hex(32)


# Hash refresh tokens before storing — compare hashes on lookup
def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# Normalize email to prevent case-sensitive duplicates
def _normalize_email(email: str) -> str:
    return email.lower().strip()


async def register(
    session: AsyncSession,
    email: str,
    password: str,
    name: str,
) -> tuple[User, str, str]:
    email = _normalize_email(email)

# Check against non-deleted users only
    existing = await session.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        password_hash=await _hash_password(password),
        full_name=name,
        tier="free",
    )
    session.add(user)
    await session.flush()

    access_token = _create_access_token(user)
    raw_refresh_token = _create_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token=_hash_refresh_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRATION),
    )
    session.add(rt)

    await logger.ainfo("user_registered", user_id=str(user.id), email=email)
    return user, access_token, raw_refresh_token


async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    email = _normalize_email(email)

    result = await session.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not await _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    user.last_login = datetime.now(timezone.utc)

    access_token = _create_access_token(user)
    raw_refresh_token = _create_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token=_hash_refresh_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRATION),
    )
    session.add(rt)

    await logger.ainfo("user_logged_in", user_id=str(user.id))
    return user, access_token, raw_refresh_token


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[User, str, str]:
# Compare hashed token
    token_hash = _hash_refresh_token(refresh_token)

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    rt = result.scalar_one_or_none()

    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if rt.expires_at < datetime.now(timezone.utc):
        rt.revoked_at = datetime.now(timezone.utc)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old token (rotation)
    rt.revoked_at = datetime.now(timezone.utc)

    # Get user
    user_result = await session.execute(
        select(User).where(User.id == rt.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Issue new pair
    access_token = _create_access_token(user)
    raw_new_refresh = _create_refresh_token()

    new_rt = RefreshToken(
        user_id=user.id,
        token=_hash_refresh_token(raw_new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_EXPIRATION),
    )
    session.add(new_rt)

    await logger.ainfo("tokens_refreshed", user_id=str(user.id))
    return user, access_token, raw_new_refresh


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User:
    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def update_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
) -> User:
    user = await get_user_by_id(session, user_id)
    user.full_name = name
    await logger.ainfo("profile_updated", user_id=str(user_id))
    return user


async def change_password(
    session: AsyncSession,
    user_id: uuid.UUID,
    old_password: str,
    new_password: str,
) -> None:
    user = await get_user_by_id(session, user_id)

    if not await _verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = await _hash_password(new_password)

    # Revoke all refresh tokens (force re-login on other devices)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )

    await logger.ainfo("password_changed", user_id=str(user_id))


async def update_tier(
    session: AsyncSession,
    user_id: uuid.UUID,
    tier: str,
) -> User:
    user = await get_user_by_id(session, user_id)
    user.tier = tier
    await logger.ainfo("tier_updated", user_id=str(user_id), tier=tier)
    return user
