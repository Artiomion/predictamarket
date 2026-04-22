"""Shared yfinance wrapper with timeout, retry, and Redis caching for macro data."""

import time
from typing import TYPE_CHECKING

import structlog
import yfinance as yf

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401  (used only in string type hints)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger()

# Circuit breaker state
_consecutive_failures: int = 0
_circuit_open_until: float = 0
_CIRCUIT_THRESHOLD = 5
_CIRCUIT_COOLDOWN = 60  # seconds


class YFinanceError(Exception):
    pass


class YFinanceRateLimited(YFinanceError):
    pass


def _check_circuit() -> None:
    """Raise if circuit breaker is open."""
    global _circuit_open_until
    if _consecutive_failures >= _CIRCUIT_THRESHOLD:
        if time.monotonic() < _circuit_open_until:
            raise YFinanceError(f"Circuit breaker open — too many failures. Retry after {_CIRCUIT_COOLDOWN}s cooldown.")
        # Cooldown passed — half-open, allow one request
        pass


def _record_success() -> None:
    global _consecutive_failures
    _consecutive_failures = 0


def _record_failure() -> None:
    global _consecutive_failures, _circuit_open_until
    _consecutive_failures += 1
    if _consecutive_failures >= _CIRCUIT_THRESHOLD:
        _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN
        logger.warning("yfinance_circuit_open", failures=_consecutive_failures, cooldown=_CIRCUIT_COOLDOWN)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((YFinanceRateLimited, ConnectionError, TimeoutError)),
    reraise=True,
)
def yf_download(
    ticker: str,
    start: str,
    progress: bool = False,
    timeout: int = 15,
) -> "pd.DataFrame":
    """yfinance download with retry + circuit breaker.

    Args:
        ticker: Symbol or list of symbols
        start: Start date string YYYY-MM-DD
        progress: Show download progress
        timeout: HTTP timeout in seconds
    """
    import pandas as pd

    _check_circuit()

    try:
        df = yf.download(ticker, start=start, progress=progress, timeout=timeout)
        if isinstance(df, pd.DataFrame) and len(df) > 0:
            _record_success()
            return df
        # Empty result — not necessarily an error, but don't count as success
        return df
    except Exception as exc:
        error_str = str(exc).lower()
        if "rate" in error_str or "429" in error_str or "too many" in error_str:
            _record_failure()
            raise YFinanceRateLimited(f"Rate limited: {exc}") from exc
        if "timeout" in error_str or "timed out" in error_str:
            _record_failure()
            raise TimeoutError(f"Timeout: {exc}") from exc
        _record_failure()
        raise YFinanceError(f"yfinance error: {exc}") from exc
