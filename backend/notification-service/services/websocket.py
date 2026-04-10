"""Socket.IO server with rooms: ticker:{TICKER}, user:{USER_ID}."""

from urllib.parse import parse_qs

import socketio
import structlog
from jose import JWTError, jwt

from shared.config import settings

logger = structlog.get_logger()

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CORS_ORIGINS.split(","),
    logger=False,
    engineio_logger=False,
)

# Store authenticated user_id per session
_session_users: dict[str, str] = {}


@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Authenticate on connect: extract JWT from query string or header."""
    query = parse_qs(environ.get("QUERY_STRING", ""))
    token = None

    # Try query param: ?token=xxx
    if "token" in query:
        token = query["token"][0]

    # Try Authorization header
    if not token:
        headers = environ.get("asgi.scope", {}).get("headers", [])
        for name, value in headers:
            if name == b"authorization":
                auth = value.decode()
                if auth.startswith("Bearer "):
                    token = auth[7:]
                break

    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                _session_users[sid] = user_id
                await logger.ainfo("ws_connect_authenticated", sid=sid, user_id=user_id)
                return
        except JWTError:
            pass

    # Allow unauthenticated connections for ticker subscriptions (public data)
    await logger.ainfo("ws_connect_anonymous", sid=sid)


@sio.event
async def disconnect(sid: str) -> None:
    _session_users.pop(sid, None)
    await logger.ainfo("ws_disconnect", sid=sid)


@sio.event
async def subscribe_ticker(sid: str, data: dict) -> None:
    """Client joins a ticker room — public, no auth needed."""
    ticker = data.get("ticker", "").upper()
    if ticker:
        await sio.enter_room(sid, f"ticker:{ticker}")
        await logger.ainfo("ws_subscribe_ticker", sid=sid, ticker=ticker)


@sio.event
async def unsubscribe_ticker(sid: str, data: dict) -> None:
    ticker = data.get("ticker", "").upper()
    if ticker:
        await sio.leave_room(sid, f"ticker:{ticker}")


@sio.event
async def subscribe_user(sid: str, data: dict) -> None:
    """FIX #1: Client can ONLY join their own user room (validated via JWT on connect)."""
    requested_user_id = data.get("user_id", "")
    authenticated_user_id = _session_users.get(sid)

    if not authenticated_user_id:
        await sio.emit("error", {"detail": "Authentication required for user subscriptions"}, to=sid)
        return

    if requested_user_id != authenticated_user_id:
        await sio.emit("error", {"detail": "Cannot subscribe to another user's notifications"}, to=sid)
        return

    await sio.enter_room(sid, f"user:{requested_user_id}")
    await logger.ainfo("ws_subscribe_user", sid=sid, user_id=requested_user_id)


async def emit_price_update(ticker: str, price_data: dict) -> None:
    await sio.emit("price:update", price_data, room=f"ticker:{ticker}")


async def emit_forecast_ready(ticker: str, forecast_data: dict) -> None:
    await sio.emit("forecast:ready", forecast_data, room=f"ticker:{ticker}")


async def emit_news_high_impact(tickers: list[str], news_data: dict) -> None:
    for ticker in tickers:
        await sio.emit("news:high_impact", news_data, room=f"ticker:{ticker}")


async def emit_alert_triggered(user_id: str, alert_data: dict) -> None:
    await sio.emit("alert:triggered", alert_data, room=f"user:{user_id}")
