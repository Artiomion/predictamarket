# PredictaMarket Backend API — Frontend Developer Reference

> All endpoints are accessed through the **API Gateway** at `http://localhost:8000`.
> Gateway handles: JWT auth, rate limiting, CORS, request logging, proxying.

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Request Conventions](#2-request-conventions)
3. [Tier System & Limits](#3-tier-system--limits)
4. [Auth Service](#4-auth-service)
5. [Market Data Service](#5-market-data-service)
6. [News Service](#6-news-service)
7. [Forecast Service](#7-forecast-service)
8. [Portfolio Service](#8-portfolio-service)
9. [Notification Service](#9-notification-service)
10. [Edgar Service](#10-edgar-service---sec-filings)
11. [WebSocket Events](#11-websocket-events)
12. [Error Handling](#12-error-handling)
13. [Response Schemas](#13-response-schemas)

---

## 1. Authentication Flow

### Registration → JWT → Refresh

```
POST /api/auth/register  →  { access_token, refresh_token, expires_in }
POST /api/auth/login     →  { access_token, refresh_token, expires_in }
POST /api/auth/refresh   →  { access_token, refresh_token }  (old refresh token invalidated)
POST /api/auth/google    →  { access_token, refresh_token, is_new_user }
```

### Using the token

```
Authorization: Bearer <access_token>
```

The gateway decodes the JWT and injects these headers to downstream services:
- `X-User-Id: <uuid>` — user's ID from JWT `sub` claim
- `X-User-Tier: free|pro|premium` — from JWT `tier` claim

**Token lifetime:**
- Access token: **15 minutes**
- Refresh token: **30 days** (single-use, rotated on each refresh)

### JWT Payload

```json
{
  "sub": "uuid-of-user",
  "email": "user@example.com",
  "tier": "free",
  "exp": 1712345678
}
```

### Public vs Protected Endpoints

| Access Level | Endpoints |
|---|---|
| **Public** (no JWT) | `GET /api/market/*`, `GET /api/news/*`, `GET /api/forecast/top-picks`, `GET /api/forecast/signals`, `GET /api/forecast/{ticker}` (read), `POST /api/auth/*` |
| **Authenticated** | `POST /api/forecast/{ticker}` (create), `**/api/portfolio/**`, `**/api/notifications/**`, `GET /api/news/feed` |
| **Pro/Premium** | `POST /api/forecast/batch`, `GET /api/edgar/*` |
| **Internal only** | `PUT /api/auth/tier` (requires `X-Internal-Key` header) |

---

## 2. Request Conventions

### Pagination

List endpoints return:
```json
{
  "data": [...],
  "total": 158,
  "page": 1,
  "per_page": 20
}
```

Query params: `?page=1&per_page=20` (per_page max: 100)

### Sorting

`GET /api/market/instruments?sort_by=market_cap&order=desc`

### Filtering

Query params: `?sector=Technology&signal=BUY&sentiment=positive`

### Dates

All dates: **ISO 8601** — `2026-04-10T12:00:00Z`

### Money

All prices/amounts: **float** with 2 decimal precision.

### Response Headers (from gateway)

```
X-Request-Id: <uuid>          — trace ID for debugging
X-RateLimit-Limit: 60         — your tier's limit
X-RateLimit-Remaining: 58     — requests left in window
X-RateLimit-Reset: 45         — seconds until window resets
```

---

## 3. Tier System & Limits

| Resource | Free | Pro ($15/mo) | Premium ($39/mo) |
|---|---|---|---|
| **Rate limit** | 60 req/min | 300 req/min | 1000 req/min |
| **Forecasts/day** | 1 | 10 | Unlimited |
| **Top Picks visible** | 5 | 20 | 20 |
| **Portfolios** | 1 | 5 | 10 |
| **Positions/portfolio** | 10 | Unlimited | Unlimited |
| **Watchlists** | 1 | 5 | 10 |
| **Watchlist items** | 10 | Unlimited | Unlimited |
| **Alerts** | 3 | 20 | Unlimited |
| **SEC Edgar** | Blocked | Full access | Full access |
| **Batch forecast** | Blocked | Full access | Full access |

---

## 4. Auth Service

**Base:** `/api/auth`

### `POST /api/auth/register`
Create new account.

**Request:**
```json
{
  "email": "user@example.com",     // required, valid email
  "password": "StrongPass123!",    // required, min 8 chars
  "name": "John Doe"               // required
}
```

**Response (201):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "a1b2c3...",
  "token_type": "bearer",
  "expires_in": 900,
  "is_new_user": true
}
```

**Errors:** `400` email already exists, `422` validation error

### `POST /api/auth/login`
```json
{ "email": "user@example.com", "password": "StrongPass123!" }
```
**Response (200):** Same as register. `is_new_user: false`

**Errors:** `401` wrong credentials

### `POST /api/auth/refresh`
```json
{ "refresh_token": "a1b2c3..." }
```
**Response (200):** New `access_token` + new `refresh_token` (old one invalidated).

**Errors:** `401` token invalid or already used

### `POST /api/auth/google`
Google OAuth — send either `id_token` or `access_token` from Google Sign-In.
```json
{ "id_token": "eyJ..." }
// or
{ "access_token": "ya29...." }
```
**Response (200/201):** Same as register. `is_new_user: true` if new account created.

### `GET /api/auth/me`  🔒
Get current user profile.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://...",
  "tier": "free",
  "is_active": true,
  "is_verified": true,
  "created_at": "2026-04-10T12:00:00Z"
}
```

### `PUT /api/auth/me`  🔒
Update profile. Body: `{ "name": "New Name" }`

### `POST /api/auth/change-password`  🔒
```json
{ "old_password": "OldPass!", "new_password": "NewPass!" }
```

---

## 5. Market Data Service

**Base:** `/api/market`

### `GET /api/market/instruments`
List all 94 S&P 500 tickers.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Items per page (max 100) |
| `sector` | string | — | Filter: `Technology`, `Healthcare`, etc. |
| `search` | string | — | Search by ticker or name |
| `sort_by` | string | `ticker` | Sort field: `ticker`, `name`, `market_cap`, `sector` |
| `order` | string | `asc` | `asc` or `desc` |

**Response (200):**
```json
{
  "total": 94,
  "page": 1,
  "per_page": 50,
  "data": [
    {
      "id": "uuid",
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "market_cap": 3200000000000,
      "exchange": "NASDAQ",
      "is_active": true
    }
  ]
}
```

### `GET /api/market/instruments/{ticker}`
Full detail for one ticker.

**Response (200):**
```json
{
  "id": "uuid",
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 3200000000000,
  "exchange": "NASDAQ",
  "is_active": true,
  "description": "Apple Inc. designs...",
  "website": "https://apple.com",
  "logo_url": "https://...",
  "ceo": "Tim Cook",
  "employees": 164000,
  "headquarters": "Cupertino, CA",
  "founded_year": 1976
}
```

### `GET /api/market/instruments/{ticker}/history`
OHLCV price history.

**Query params:** `period` = `1m|3m|6m|1y|5y` (default: `1y`), `interval` = `1d|1wk|1mo`

**Response (200):**
```json
[
  { "date": "2026-04-09", "open": 258.5, "high": 262.0, "low": 257.1, "close": 260.49, "volume": 45000000 }
]
```

### `GET /api/market/instruments/{ticker}/price`
Current/latest price.

**Response (200):**
```json
{
  "ticker": "AAPL",
  "price": 260.49,
  "change": 2.15,
  "change_pct": 0.83,
  "updated_at": "2026-04-10T16:00:00Z"
}
```

### `GET /api/market/instruments/{ticker}/financials`
Financial metrics. Query: `?period=annual|quarterly`

**Response (200):** Array of `FinancialMetricResponse`

### `GET /api/earnings/upcoming`
Upcoming earnings reports. Query: `?days=30` (default: 14)

**Response (200):** Array of `EarningsCalendarResponse`

### `GET /api/earnings/{ticker}/history`
Historical earnings with beat/miss.

**Response (200):** Array of `EarningsResultResponse`

### `GET /api/insider/{ticker}`
Insider transactions. Query: `?limit=20`

**Response (200):** Array of `InsiderTransactionResponse`

---

## 6. News Service

**Base:** `/api/news`

### `GET /api/news/news`
All articles with filters.

**Query params:**
| Param | Type | Description |
|---|---|---|
| `ticker` | string | Filter by ticker |
| `source` | string | Filter by source |
| `sentiment` | string | `positive`, `negative`, `neutral` |
| `impact` | string | `high`, `medium`, `low` |
| `page` | int | Page number |
| `per_page` | int | Items per page |

**Response (200):**
```json
{
  "total": 158,
  "page": 1,
  "per_page": 20,
  "data": [
    {
      "id": "uuid",
      "title": "Apple Reports Record Quarter",
      "url": "https://...",
      "source": "MarketWatch",
      "published_at": "2026-04-10T13:00:00Z",
      "summary": "Apple reported...",
      "sentiment_score": 0.89,
      "sentiment_label": "positive",
      "impact_level": "high",
      "tickers": ["AAPL"]
    }
  ]
}
```

### `GET /api/news/news/{ticker}`
News filtered by ticker. Pagination: `?page=1&per_page=20`

### `GET /api/news/news/{ticker}/sentiment`
Daily sentiment trend. Query: `?days=30`

**Response (200):**
```json
[
  {
    "date": "2026-04-10",
    "avg_sentiment": 0.72,
    "news_count": 5,
    "positive_count": 3,
    "negative_count": 1,
    "neutral_count": 1
  }
]
```

### `GET /api/news/feed`  🔒
Personalized news feed based on user's watchlist/portfolio tickers.

---

## 7. Forecast Service

**Base:** `/api/forecast`

### `GET /api/forecast/top-picks`
Top stocks ranked by predicted return + BUY signal.

**Query:** `?limit=20`
**Headers:** `X-User-Tier` controls how many picks are visible (free=5, pro/premium=20)

**Response (200):**
```json
[
  {
    "ticker": "MSFT",
    "name": "Microsoft Corporation",
    "current_close": 373.07,
    "predicted_return_1m": 6.59,
    "signal": "BUY",
    "confidence": "MEDIUM"
  }
]
```

### `GET /api/forecast/signals`
Filter stocks by signal/confidence.

**Query:** `?signal=BUY&confidence=HIGH`

**Response (200):** Array of `ForecastFromDB`

### `POST /api/forecast/{ticker}`  🔒
Run live TFT inference (~5-6 seconds).

**Response (201):**
```json
{
  "ticker": "AAPL",
  "current_close": 260.49,
  "signal": "SELL",
  "confidence": "MEDIUM",
  "forecast": {
    "1d":  { "median": 248.08, "lower_80": 219.53, "upper_80": 273.91, "lower_95": 192.66, "upper_95": 284.83 },
    "3d":  { "median": 242.44, "lower_80": 214.03, "upper_80": 271.09, "lower_95": 187.85, "upper_95": 282.08 },
    "1w":  { "median": 244.28, "lower_80": 213.95, "upper_80": 271.64, "lower_95": 187.08, "upper_95": 284.06 },
    "2w":  { "median": 242.20, "lower_80": 207.24, "upper_80": 276.79, "lower_95": 177.54, "upper_95": 296.29 },
    "1m":  { "median": 241.97, "lower_80": 200.44, "upper_80": 288.41, "lower_95": 167.19, "upper_95": 318.02 }
  },
  "full_curve": [248.08, 242.77, 242.44, "...22 values total (trading days)..."],
  "variable_importance": {
    "top_factors": [
      { "name": "Low", "weight": 0.0623, "direction": "bearish", "is_estimated": false },
      { "name": "oil", "weight": 0.0456, "direction": "bearish", "is_estimated": false },
      { "name": "eps_surprise_pct", "weight": 0.0195, "direction": "bearish", "is_estimated": false }
    ]
  },
  "inference_time_s": 6.2,
  "forecast_date": "2026-04-10",
  "predicted_return_1d": -4.76,
  "predicted_return_1w": -6.22,
  "predicted_return_1m": -7.1,
  "news_articles_used": 3,
  "persisted": true
}
```

**Key concepts for frontend:**
- `signal`: `BUY` | `SELL` | `HOLD`
- `confidence`: `HIGH` | `MEDIUM` | `LOW`
- `full_curve`: 22 median prices (one per trading day, ~1 month) — plot as forecast line on chart
- `forecast.{horizon}`: CI bands at 80% and 95% — plot as shaded areas
- `variable_importance.top_factors`: for "What's driving this?" waterfall chart
- `is_estimated: true` = fallback factors when model attention extraction fails
- `persisted: false` = inference succeeded but DB save failed

**Errors:** `401` no auth, `404` ticker not in S&P 500 set, `429` daily limit reached

### `GET /api/forecast/{ticker}`
Get latest stored forecast (no inference, instant).

### `GET /api/forecast/{ticker}/history`
Forecast history. Query: `?limit=30`

**Response (200):** Array of `ForecastFromDB`

### `POST /api/forecast/batch`  🔒 Pro+
Queue batch forecast for multiple tickers.

**Request:** `{ "tickers": ["AAPL", "MSFT", "NVDA"] }`

**Response (201):** `{ "job_id": "abc123", "status": "queued", "tickers": [...] }`

### `GET /api/forecast/batch/{job_id}`
Poll batch job status.

**Response (200):** `{ "job_id": "abc123", "status": "completed", "completed": 3, "total": 3, "results": [...] }`

---

## 8. Portfolio Service

**Base:** `/api/portfolio`  — All endpoints require auth 🔒

### Portfolios

#### `POST /api/portfolio/portfolios`
```json
{ "name": "My Portfolio", "description": "Tech stocks" }
```
**Response (201):** `PortfolioResponse`

#### `GET /api/portfolio/portfolios`
List user's portfolios.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "My Portfolio",
    "description": "Tech stocks",
    "is_default": true,
    "total_value": 25000.00,
    "total_pnl": 1500.00,
    "total_pnl_pct": 6.38,
    "created_at": "2026-04-10T12:00:00Z"
  }
]
```

#### `GET /api/portfolio/portfolios/{id}` — Single portfolio
#### `DELETE /api/portfolio/portfolios/{id}` — Soft delete

### Positions

#### `POST /api/portfolio/portfolios/{id}/positions`
```json
{ "ticker": "AAPL", "quantity": 10, "price": 250.00, "notes": "Buy the dip" }
```
**Response (201):**
```json
{
  "id": "uuid",
  "ticker": "AAPL",
  "quantity": 10,
  "avg_buy_price": 250.00,
  "current_price": 260.49,
  "pnl": 104.90,
  "pnl_pct": 4.20
}
```

Buying same ticker again → weighted average price recalculated.

#### `GET /api/portfolio/portfolios/{id}/positions`
All positions in portfolio. Response: array of `PositionResponse`

#### `DELETE /api/portfolio/portfolios/{id}/positions/{ticker}`
Sell position. Query: `?quantity=5&price=260.00` (partial sell) or omit for full sell.

### Analytics

#### `GET /api/portfolio/portfolios/{id}/analytics`
```json
{
  "total_value": 25000.00,
  "total_pnl": 1500.00,
  "total_pnl_pct": 6.38,
  "positions_count": 5,
  "best_position": "NVDA",
  "worst_position": "META"
}
```

#### `GET /api/portfolio/portfolios/{id}/sectors`
```json
[
  { "sector": "Technology", "value": 15000.00, "pct": 60.0 },
  { "sector": "Healthcare", "value": 10000.00, "pct": 40.0 }
]
```

#### `GET /api/portfolio/portfolios/{id}/transactions`
Trade history. Query: `?limit=50`. Response: array of `TransactionResponse`

#### `GET /api/portfolio/portfolios/{id}/export`
Download CSV. Response: `Content-Type: text/csv`

### Watchlists

#### `POST /api/portfolio/watchlists`
```json
{ "name": "Tech Watch" }
```
**Response (201):** `WatchlistResponse`

#### `GET /api/portfolio/watchlists` — List all
#### `GET /api/portfolio/watchlists/{id}` — Detail with items

```json
{
  "id": "uuid",
  "name": "Tech Watch",
  "created_at": "2026-04-10T12:00:00Z",
  "items": [
    { "id": "uuid", "ticker": "AAPL", "added_at": "2026-04-10T12:00:00Z" },
    { "id": "uuid", "ticker": "MSFT", "added_at": "2026-04-10T12:05:00Z" }
  ]
}
```

#### `POST /api/portfolio/watchlists/{id}/items`
```json
{ "ticker": "NVDA" }
```

#### `DELETE /api/portfolio/watchlists/{id}/items/{ticker}`

---

## 9. Notification Service

**Base:** `/api/notifications`  — All endpoints require auth 🔒

### `POST /api/notifications/alerts`
```json
{
  "ticker": "AAPL",
  "alert_type": "price_above",
  "condition_value": 270.00
}
```

**Alert types:** `price_above`, `price_below`, `forecast_change`, `news_high_impact`, `earnings_upcoming`

**Response (201):** `AlertResponse`

### `GET /api/notifications/alerts`
List active alerts. Query: `?limit=50`

### `DELETE /api/notifications/alerts/{id}`

### `GET /api/notifications/alerts/history`
Triggered notification log. Query: `?limit=50`

**Response (200):**
```json
[
  {
    "id": "uuid",
    "channel": "in_app",
    "title": "Price Alert: AAPL",
    "body": "AAPL crossed above $270.00 — current price $271.50",
    "is_read": false,
    "created_at": "2026-04-10T15:30:00Z"
  }
]
```

---

## 10. Edgar Service — SEC Filings

**Base:** `/api/edgar`  — Pro/Premium only 🔒

### `GET /api/edgar/{ticker}/filings`
SEC filings list. Query: `?filing_type=10-K&limit=10`

### `GET /api/edgar/{ticker}/income`
Income statements. Query: `?limit=8`

**Response (200):**
```json
[
  {
    "period_end": "2025-12-31",
    "revenue": 394000000000,
    "cost_of_revenue": 214000000000,
    "gross_profit": 180000000000,
    "operating_income": 120000000000,
    "net_income": 97000000000,
    "eps_basic": 6.42,
    "eps_diluted": 6.38,
    "shares_outstanding": 15100000000
  }
]
```

### `GET /api/edgar/{ticker}/balance`
Balance sheets. Query: `?limit=8`

### `GET /api/edgar/{ticker}/cashflow`
Cash flow statements. Query: `?limit=8`

**Error:** `403` for free tier users.

---

## 11. WebSocket Events

**Endpoint:** `ws://localhost:8006/socket.io/` (Socket.IO protocol)

### Connection

```javascript
import { io } from "socket.io-client";

// Authenticated (for personal alerts)
const socket = io("http://localhost:8006", {
  query: { token: accessToken }
});

// Or anonymous (for price updates only)
const socket = io("http://localhost:8006");
```

### Client → Server Events

| Event | Payload | Auth Required | Description |
|---|---|---|---|
| `subscribe_ticker` | `{ "ticker": "AAPL" }` | No | Join ticker room for price updates |
| `unsubscribe_ticker` | `{ "ticker": "AAPL" }` | No | Leave ticker room |
| `subscribe_user` | `{ "user_id": "uuid" }` | Yes | Join personal room (must match JWT) |

### Server → Client Events

| Event | Room | Payload |
|---|---|---|
| `price:update` | `ticker:{TICKER}` | `{ "ticker": "AAPL", "price": 260.49, "change": 2.15, "change_pct": 0.83 }` |
| `forecast:ready` | `ticker:{TICKER}` | `{ "ticker": "AAPL", "signal": "BUY", "confidence": "HIGH", ... }` |
| `news:high_impact` | `ticker:{TICKER}` | `{ "title": "...", "sentiment": "positive", "impact": "high", "tickers": ["AAPL"] }` |
| `alert:triggered` | `user:{USER_ID}` | `{ "alert_id": "uuid", "ticker": "AAPL", "message": "AAPL crossed $270", "price": 271.5 }` |
| `error` | direct to sid | `{ "detail": "Authentication required" }` |

---

## 12. Error Handling

### Error Format

All errors return:
```json
{ "detail": "Human-readable error message" }
```

### HTTP Status Codes

| Code | Meaning | When |
|---|---|---|
| `200` | OK | Successful GET, PUT |
| `201` | Created | Successful POST (register, create portfolio, run forecast) |
| `400` | Bad Request | Invalid input (email already exists, missing fields) |
| `401` | Unauthorized | Missing/expired/invalid JWT |
| `403` | Forbidden | Wrong tier, not your resource, internal endpoint |
| `404` | Not Found | Ticker not in S&P 500, resource doesn't exist |
| `422` | Validation Error | Pydantic validation failed (wrong types, constraints) |
| `429` | Rate Limited | Too many requests or daily forecast limit reached |
| `500` | Internal Error | Server error |
| `502` | Bad Gateway | Upstream service unavailable |

### 422 Validation Error Detail

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 13. Response Schemas

### Signal & Confidence Colors

```
BUY  + HIGH   → #00FF88 (bright green) + badge "99.5% WR"
BUY  + MEDIUM → #00FF88 (green)
SELL + HIGH   → #FF3366 (bright red)
SELL + MEDIUM → #FF3366 (red)
HOLD + LOW    → #FFB800 (amber)
```

### Forecast Horizons

| Key | Trading Days | Human Label |
|---|---|---|
| `1d` | 1 | Tomorrow |
| `3d` | 3 | 3 Days |
| `1w` | 5 | 1 Week |
| `2w` | 10 | 2 Weeks |
| `1m` | 22 | 1 Month |

### Confidence Intervals

- **80% CI** = `[lower_80, upper_80]` — shaded area on chart (primary)
- **95% CI** = `[lower_95, upper_95]` — lighter shaded area (secondary)
- **Median** = center forecast line

### Full Curve (22 points)

`full_curve[i]` = median predicted price for trading day `i+1` from today.
Use for drawing the forecast line on the TradingView chart overlay.

### Sectors (from instruments)

`Technology`, `Healthcare`, `Financial Services`, `Consumer Cyclical`, `Communication Services`, `Industrials`, `Consumer Defensive`, `Energy`, `Utilities`, `Real Estate`, `Basic Materials`

### 94 Supported Tickers

The platform supports exactly **94 S&P 500 tickers** that were in the TFT model's training set. File: `models/old_model_sp500_tickers.txt`. Any ticker not in this set returns `404`.
