import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import settings  # noqa: E402
from shared.logging import setup_logging  # noqa: E402
from shared.monitoring import init_sentry, metrics_router, MetricsMiddleware  # noqa: E402

setup_logging()
init_sentry()

from middleware.jwt_auth import JWTAuthMiddleware  # noqa: E402
from middleware.rate_limit import RateLimitMiddleware  # noqa: E402
from middleware.logging import RequestLoggingMiddleware  # noqa: E402
from routers.proxy import router as proxy_router  # noqa: E402
from routers.health import router as health_router  # noqa: E402
from services.proxy_client import proxy_client  # noqa: E402

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("api-gateway starting", port=8000)
    await proxy_client.start()
    yield
    await proxy_client.stop()
    await logger.ainfo("api-gateway stopped")


app = FastAPI(
    title="PredictaMarket API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id", "X-User-Tier", "X-Internal-Key", "X-Request-Id"],
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(proxy_router)
