"""Shared auth dependencies for all microservices."""

import uuid

from fastapi import Header, HTTPException


def require_user_id(x_user_id: str | None = Header(None)) -> uuid.UUID:
    """Extract and validate user ID from X-User-Id header (set by api-gateway)."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID")
