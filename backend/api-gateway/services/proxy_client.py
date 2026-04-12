import httpx
import structlog

from shared.config import settings

logger = structlog.get_logger()

# Route prefix → upstream base URL (from config, so Docker service names work)
SERVICE_MAP: dict[str, str] = {
    "/api/auth":      settings.AUTH_SERVICE_URL,
    "/api/billing":   settings.AUTH_SERVICE_URL,
    "/api/market":    settings.MARKET_SERVICE_URL,
    "/api/earnings":  settings.MARKET_SERVICE_URL,
    "/api/insider":   settings.MARKET_SERVICE_URL,
    "/api/news":      settings.NEWS_SERVICE_URL,
    "/api/forecast":  settings.FORECAST_SERVICE_URL,
    "/api/portfolio":      settings.PORTFOLIO_SERVICE_URL,
    "/api/notifications":  settings.NOTIFICATION_SERVICE_URL,
    "/api/edgar":          settings.EDGAR_SERVICE_URL,
}


class ProxyClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
        await logger.ainfo("proxy_client started")

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            await logger.ainfo("proxy_client stopped")

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("ProxyClient not started — call start() first")
        return self._client

    def resolve_upstream(self, path: str) -> tuple[str, str] | None:
        """Return (base_url, upstream_path) for the given request path.

        Forwards the full original path to upstream — each service owns its
        own prefix (e.g. auth-service mounts at /api/auth).
        """
        for prefix, base_url in SERVICE_MAP.items():
            if path.startswith(prefix):
                return base_url, path
        return None

    async def forward(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        query_string: str,
    ) -> httpx.Response:
        resolved = self.resolve_upstream(path)
        if resolved is None:
            raise ValueError(f"No upstream for path: {path}")

        base_url, upstream_path = resolved
        url = f"{base_url}{upstream_path}"
        if query_string:
            url = f"{url}?{query_string}"

        # Strip hop-by-hop headers
        forward_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in ("host", "connection", "transfer-encoding")
        }

        response = await self.client.request(
            method=method,
            url=url,
            headers=forward_headers,
            content=body,
        )
        return response


proxy_client = ProxyClient()
