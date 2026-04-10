import base64
import json
import time
import uuid

import httpx
import pytest

BASE = "http://localhost:8001/api/auth"
_RUN = uuid.uuid4().hex[:8]  # unique per test run to avoid DB conflicts


class TestRegister:
    def test_success(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": f"alice-{_RUN}@test.com", "password": "Password123!", "name": "Alice"},
        )
        assert r.status_code == 201
        assert "access_token" in r.json()
        assert "refresh_token" in r.json()

    def test_duplicate_email(self) -> None:
        httpx.post(
            f"{BASE}/register",
            json={"email": f"dup-{_RUN}@test.com", "password": "Pass123!", "name": "A"},
        )
        r = httpx.post(
            f"{BASE}/register",
            json={"email": f"dup-{_RUN}@test.com", "password": "Pass123!", "name": "B"},
        )
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower() or "exist" in r.json()["detail"].lower()

    def test_invalid_email(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": "not-an-email", "password": "Pass123!", "name": "X"},
        )
        assert r.status_code == 422

    def test_short_password(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": "short@test.com", "password": "123", "name": "X"},
        )
        assert r.status_code in [400, 422]

    def test_missing_name(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": "noname@test.com", "password": "Pass123!"},
        )
        assert r.status_code == 422


class TestLogin:
    def setup_method(self) -> None:
        httpx.post(
            f"{BASE}/register",
            json={"email": f"login-{_RUN}@test.com", "password": "Pass123!", "name": "L"},
        )

    def test_success(self) -> None:
        r = httpx.post(
            f"{BASE}/login",
            json={"email": f"login-{_RUN}@test.com", "password": "Pass123!"},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_wrong_password(self) -> None:
        r = httpx.post(
            f"{BASE}/login",
            json={"email": f"login-{_RUN}@test.com", "password": "WrongPass!"},
        )
        assert r.status_code == 401

    def test_nonexistent_user(self) -> None:
        r = httpx.post(
            f"{BASE}/login",
            json={"email": "nobody@test.com", "password": "Pass123!"},
        )
        assert r.status_code == 401


class TestJWTPayload:
    def test_payload_fields(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": f"jwt-{_RUN}@test.com", "password": "Pass123!", "name": "JWT"},
        )
        token = r.json()["access_token"]
        # Decode payload without verification
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        payload = json.loads(base64.b64decode(part))
        assert "sub" in payload, "No sub in JWT"
        assert "email" in payload, "No email in JWT"
        assert "tier" in payload, "No tier in JWT"
        assert payload["tier"] == "free", f"New user should be free, got {payload['tier']}"
        assert "exp" in payload, "No exp in JWT"
        # access_token lives ~15 min (900 sec)
        ttl = payload["exp"] - time.time()
        assert 0 < ttl < 1000, f"access_token TTL incorrect: {ttl}"


class TestRefreshToken:
    def test_rotation(self) -> None:
        r = httpx.post(
            f"{BASE}/register",
            json={"email": f"refresh-{_RUN}@test.com", "password": "Pass123!", "name": "R"},
        )
        old_refresh = r.json()["refresh_token"]
        # First refresh — OK
        r1 = httpx.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
        assert r1.status_code == 200
        new_refresh = r1.json()["refresh_token"]
        assert new_refresh != old_refresh, "Refresh token must rotate"
        # Old one no longer works
        r2 = httpx.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
        assert r2.status_code == 401, "Old refresh_token must be rejected"

    def test_invalid_refresh_token(self) -> None:
        r = httpx.post(f"{BASE}/refresh", json={"refresh_token": "invalid.token.here"})
        assert r.status_code == 401


class TestChangePassword:
    def test_change_and_login_with_new(self) -> None:
        email = f"chpw-{_RUN}@test.com"
        old_pw = "OldPass123!"
        new_pw = "NewPass456!"
        reg = httpx.post(
            f"{BASE}/register",
            json={"email": email, "password": old_pw, "name": "ChPw"},
        )
        # Get user_id from JWT
        token = reg.json()["access_token"]
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        user_id = json.loads(base64.b64decode(part))["sub"]

        r = httpx.post(
            f"{BASE}/change-password",
            json={"old_password": old_pw, "new_password": new_pw},
            headers={"X-User-Id": user_id},
        )
        assert r.status_code == 200

        # New password works
        assert (
            httpx.post(f"{BASE}/login", json={"email": email, "password": new_pw}).status_code
            == 200
        )
        # Old password doesn't work
        assert (
            httpx.post(f"{BASE}/login", json={"email": email, "password": old_pw}).status_code
            == 401
        )
