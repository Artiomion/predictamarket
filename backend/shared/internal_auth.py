"""Shared internal service-to-service authentication dependency."""

import hmac

from fastapi import Header, HTTPException

from shared.config import settings


def require_internal_key(x_internal_key: str | None = Header(None)) -> str:
    """Verify internal service-to-service API key (constant-time comparison)."""
    if not x_internal_key or not hmac.compare_digest(x_internal_key, settings.INTERNAL_API_KEY):
        raise HTTPException(status_code=403, detail="Forbidden: internal endpoint")
    return x_internal_key
