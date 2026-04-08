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

from routers.health import router as health_router  # noqa: E402
from routers.instruments import router as instruments_router  # noqa: E402
from routers.earnings import router as earnings_router  # noqa: E402
from routers.insider import router as insider_router  # noqa: E402

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("market-data-service starting", port=8002)
    yield
    await logger.ainfo("market-data-service stopped")


app = FastAPI(
    title="PredictaMarket Market Data Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(instruments_router, prefix="/api/market", tags=["market"])
app.include_router(earnings_router, prefix="/api/earnings", tags=["earnings"])
app.include_router(insider_router, prefix="/api/insider", tags=["insider"])
