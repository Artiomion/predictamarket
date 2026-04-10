"""
ТЕСТ 6 — Rate limiting.

auth-service не запущен, поэтому тестируем анонимный rate limit по IP.
Free tier (default for anonymous): 60 req/min.
Отправляем 65 запросов и проверяем что получаем 429.
"""

import httpx
import pytest


def test_rate_limit() -> None:
    statuses: list[int] = []
    with httpx.Client(base_url="http://localhost:8000") as c:
        for i in range(65):
            r = c.get("/api/market/instruments")
            statuses.append(r.status_code)
            if i == 0:
                limit = r.headers.get("x-ratelimit-limit")
                remaining = r.headers.get("x-ratelimit-remaining")
                print(f"  First request: status={r.status_code}, limit={limit}, remaining={remaining}")

    got_429 = 429 in statuses
    count_429 = statuses.count(429)

    print(f"  Total requests: {len(statuses)}")
    print(f"  429 (rate limited):  {count_429}")

    if got_429:
        first_429 = statuses.index(429) + 1
        print(f"  First 429 at request #{first_429}")

    assert got_429, f"Rate limiting did not trigger after {len(statuses)} requests"
