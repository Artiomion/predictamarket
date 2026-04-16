import sys
from pathlib import Path

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.config import settings  # noqa: E402

# Routes that do NOT require authentication
PUBLIC_ROUTES: list[tuple[str, set[str]]] = [
    ("/health",                            {"GET"}),
    ("/metrics",                           {"GET"}),
    ("/api/auth/register",                 {"POST"}),
    ("/api/auth/login",                    {"POST"}),
    ("/api/auth/refresh",                  {"POST"}),
    ("/api/auth/google",                   {"POST"}),
    ("/api/market/instruments",            {"GET"}),
    ("/api/earnings/upcoming",             {"GET"}),
    ("/api/billing/webhook",               {"POST"}),
    ("/api/billing/plans",                 {"GET"}),
    ("/api/finnhub/candles",               {"GET"}),
]

# Prefix-based public GET routes (e.g. /api/market/instruments/AAPL/*)
PUBLIC_PREFIXES_GET: list[str] = [
    "/api/market/instruments/",
]


def _is_public(path: str, method: str) -> bool:
    for route_path, methods in PUBLIC_ROUTES:
        if path == route_path and method in methods:
            return True
    if method == "GET":
        for prefix in PUBLIC_PREFIXES_GET:
            if path.startswith(prefix):
                return True
    return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user_id = None
        request.state.user_tier = None

        # CORS preflight — let CORSMiddleware handle it
        if request.method == "OPTIONS":
            return await call_next(request)

        if _is_public(request.url.path, request.method):
            # Still decode token if present (for tier-aware responses on public routes)
            self._try_decode(request)
            return await call_next(request)

        # Non-public routes require a valid token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        request.state.user_id = payload.get("sub")
        request.state.user_tier = payload.get("tier", "free")

        return await call_next(request)

    def _try_decode(self, request: Request) -> None:
        """Attempt to decode a token on public routes without rejecting."""
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return
        try:
            payload = jwt.decode(
                auth_header[7:],
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            request.state.user_id = payload.get("sub")
            request.state.user_tier = payload.get("tier", "free")
        except JWTError:
            pass
