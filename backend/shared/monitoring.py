"""Shared monitoring — Sentry integration + Prometheus metrics endpoint.

Usage in each service's main.py:
    from shared.monitoring import init_sentry, metrics_router
    init_sentry()
    app.include_router(metrics_router)
"""

import time
from collections import defaultdict

import structlog
from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.config import settings

logger = structlog.get_logger()

# ── Sentry ────────────────────────────────────────────────────────────────────

def init_sentry() -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("sentry_initialized", environment=settings.APP_ENV)
    except ImportError:
        logger.warning("sentry_sdk_not_installed")


# ── Prometheus-style metrics ──────────────────────────────────────────────────

_request_count: dict[str, int] = defaultdict(int)
_request_duration: dict[str, float] = defaultdict(float)
_error_count: dict[str, int] = defaultdict(int)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request count, duration, and error metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        method = request.method
        path = request.url.path
        status = response.status_code
        key = f"{method} {path}"

        _request_count[key] += 1
        _request_duration[key] += duration

        if status >= 500:
            _error_count[key] += 1

        return response


metrics_router = APIRouter()


@metrics_router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics endpoint."""
    lines = []

    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    for key, count in sorted(_request_count.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_requests_total{{method="{method}",path="{path}"}} {count}')

    lines.append("# HELP http_request_duration_seconds Total request duration")
    lines.append("# TYPE http_request_duration_seconds counter")
    for key, dur in sorted(_request_duration.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_request_duration_seconds{{method="{method}",path="{path}"}} {dur:.4f}')

    lines.append("# HELP http_errors_total Total 5xx errors")
    lines.append("# TYPE http_errors_total counter")
    for key, count in sorted(_error_count.items()):
        method, path = key.split(" ", 1)
        lines.append(f'http_errors_total{{method="{method}",path="{path}"}} {count}')

    return Response(content="\n".join(lines) + "\n", media_type="text/plain")
