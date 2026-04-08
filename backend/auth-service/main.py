import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.logging import setup_logging  # noqa: E402
from shared.monitoring import init_sentry

setup_logging()
init_sentry()

from routers.auth import router as auth_router  # noqa: E402
from routers.health import router as health_router  # noqa: E402

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("auth-service starting", port=8001)
    yield
    await logger.ainfo("auth-service stopped")


app = FastAPI(
    title="PredictaMarket Auth Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
