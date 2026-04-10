import structlog
from fastapi import APIRouter, Request, Response

from services.proxy_client import proxy_client

logger = structlog.get_logger()
router = APIRouter()


@router.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_request(request: Request, path: str) -> Response:
    full_path = f"/api/{path}"
    resolved = proxy_client.resolve_upstream(full_path)

    if resolved is None:
        return Response(
            content='{"detail":"Route not found"}',
            status_code=404,
            media_type="application/json",
        )

    body = await request.body()
    headers = dict(request.headers)

    # SECURITY: strip trusted headers that downstream services rely on —
    # prevents unauthenticated clients from injecting x-user-id/x-user-tier
    for h in ("x-user-id", "x-user-tier", "x-internal-key"):
        headers.pop(h, None)

    # Inject user context from JWT middleware (set in request.state)
    user_id = getattr(request.state, "user_id", None)
    user_tier = getattr(request.state, "user_tier", None)
    request_id = getattr(request.state, "request_id", None)
    if user_id:
        headers["x-user-id"] = str(user_id)
    if user_tier:
        headers["x-user-tier"] = user_tier
    if request_id:
        headers["x-request-id"] = request_id

    try:
        upstream_response = await proxy_client.forward(
            method=request.method,
            path=full_path,
            headers=headers,
            body=body,
            query_string=request.url.query or "",
        )
    except Exception as exc:
        await logger.aerror("proxy_error", path=full_path, error=str(exc))
        return Response(
            content='{"detail":"Service unavailable"}',
            status_code=502,
            media_type="application/json",
        )

    # Strip hop-by-hop headers from response
    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k.lower() not in ("transfer-encoding", "connection", "content-encoding", "content-length")
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type", "application/json"),
    )
