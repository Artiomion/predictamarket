"""SEC EDGAR API client with rate limiting (max 10 req/sec)."""

import asyncio
import time

import httpx
import structlog

from shared.redis_client import redis_client

logger = structlog.get_logger()

SEC_BASE = "https://data.sec.gov"
SEC_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "PredictaMarket contact@predictamarket.com"
RATE_LIMIT_DELAY = 0.12  # 10 req/sec → 100ms between requests + margin


class SECClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request: float = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def _rate_limited_get(self, url: str) -> httpx.Response:
        """GET with SEC rate limiting (max 10 req/sec)."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < RATE_LIMIT_DELAY:
            await asyncio.sleep(RATE_LIMIT_DELAY - elapsed)

        client = await self._get_client()
        self._last_request = time.monotonic()
        response = await client.get(url)
        response.raise_for_status()
        return response

    async def get_cik_for_ticker(self, ticker: str) -> str | None:
        """Resolve ticker → CIK (10-digit zero-padded). Cached in Redis."""
        ticker_upper = ticker.upper()
        cache_key = f"edgar:cik:{ticker_upper}"
        cached = await redis_client.get(cache_key)
        if cached:
            return cached

        try:
            response = await self._rate_limited_get(SEC_COMPANY_TICKERS)
            data = response.json()

            # data is {0: {cik_str, ticker, title}, 1: ...}
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"]).zfill(10)
                    await redis_client.set(cache_key, cik, ex=86400)  # 24h cache
                    return cik
        except Exception as exc:
            await logger.aerror("cik_lookup_error", ticker=ticker_upper, error=str(exc))

        return None

    async def get_company_facts(self, cik: str) -> dict | None:
        """Fetch XBRL company facts from SEC EDGAR."""
        url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        try:
            response = await self._rate_limited_get(url)
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                await logger.awarning("no_edgar_data", cik=cik)
                return None
            raise
        except Exception as exc:
            await logger.aerror("edgar_fetch_error", cik=cik, error=str(exc))
            return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


sec_client = SECClient()
