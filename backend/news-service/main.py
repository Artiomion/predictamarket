import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

_app_dir = Path(__file__).resolve().parent
for _p in [_app_dir.parent, _app_dir]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from shared.logging import setup_logging  # noqa: E402

setup_logging()

from routers.health import router as health_router  # noqa: E402
from routers.news import router as news_router  # noqa: E402

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("news-service starting", port=8003)
    yield
    await logger.ainfo("news-service stopped")


app = FastAPI(
    title="PredictaMarket News Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(news_router, prefix="/api/news", tags=["news"])
