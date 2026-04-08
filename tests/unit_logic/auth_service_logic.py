"""Extracted auth business logic — no DB/Redis dependencies."""

import hashlib
import secrets


def normalize_email(email: str) -> str:
    return email.lower().strip()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> str:
    return secrets.token_hex(32)
