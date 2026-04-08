import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import socketio
import structlog
from fastapi import FastAPI

_app_dir = Path(__file__).resolve().parent
for _p in [_app_dir.parent, _app_dir]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from shared.logging import setup_logging  # noqa: E402

setup_logging()

from routers.health import router as health_router  # noqa: E402
from routers.alerts import router as alerts_router  # noqa: E402
from services.websocket import sio  # noqa: E402
from services.background import start_background_tasks, stop_background_tasks  # noqa: E402

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("notification-service starting", port=8006)
    await start_background_tasks()
    yield
    await stop_background_tasks()
    await logger.ainfo("notification-service stopped")


app = FastAPI(title="PredictaMarket Notification Service", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(alerts_router, prefix="/api/notifications", tags=["notifications"])

# Mount Socket.IO as ASGI sub-app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Re-export for uvicorn: `uvicorn main:socket_app`
