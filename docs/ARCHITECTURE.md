# Architecture

System design, service boundaries, data flow, and key decisions.

**Audience:** engineers onboarding the codebase or evaluating scaling
trade-offs.

---

## 1. Context

PredictaMarket serves two kinds of user-facing value:

1. **Ranking:** for each of 346 S&P 500 stocks, predict expected 1-month
   return and rank the universe.
2. **Consensus filter:** surface a small subset of "high-conviction" BUYs
   where three trained models all agree.

Both outputs come from the same TFT ensemble; what differs is the
post-processing rule and the UI surface.

**Not in scope:** order routing / broker integration, options, crypto,
international equities.

---

## 2. Component Diagram

```
                               ┌──────────────────┐
                               │   Users (web)    │
                               └────────┬─────────┘
                                        │ HTTPS
                                        ▼
                     ┌────────────────────────────────────┐
                     │  Next.js 14 frontend (:3000)       │
                     │  · App Router + TypeScript strict  │
                     │  · Zustand state · Framer Motion   │
                     │  · TradingView + Finnhub WS        │
                     └─────────────────┬──────────────────┘
                                       │
                 ┌─────────────────────┤  /api/*
                 │                     │
  Finnhub WS    ▼                     ▼
  (live prices) │          ┌──────────────────────────────┐
                │          │  API Gateway (:8000)         │
                │          │  · JWT validation            │
                │          │  · Rate limit (Redis Lua)    │
                │          │  · Strip X-User-* headers    │
                │          │  · CORS + request tracing    │
                │          └──┬──┬──┬──┬──┬──┬──┬──┬──────┘
                │             │  │  │  │  │  │  │  │
                │             ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼
                │   ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐
                │   │ auth   │market  │news    │forecast│portfol.│notif.  │edgar   │
                │   │ :8001  │:8002   │:8003   │:8004   │:8005   │:8006   │:8007   │
                │   └────┬───┴────┬───┴────┬───┴────┬───┴────┬───┴────┬───┴────┬───┘
                │        │        │        │        │        │        │        │
                │        └────────┴───┬────┴────────┴────────┴────────┴────────┘
                │                     │
  WebSocket ◀───┼─────────────────────┤
  (:8006)       │                     │
                │                     ▼
                │           ┌───────────────────────┐
                │           │  PostgreSQL 15        │
                │           │  9 schemas · 33 tables│
                │           └───────────────────────┘
                │                     │
                │                     │ pub/sub, rate-limit
                │                     ▼
                │           ┌───────────────────────┐
                │           │  Redis 7              │
                │           │  cache + channels     │
                │           └───────────────────────┘
                │                     ▲
                │                     │ writes from
                │                     │
                │  ┌───────────────────────────────────────┐
                └─►│  Airflow (:8080) — 13 DAGs           │
                   │  · yfinance OHLCV, macro              │
                   │  · RSS → FinBERT → PCA                │
                   │  · FRED (CPI, unemployment)           │
                   │  · SEC EDGAR XBRL                     │
                   │  · Hourly batch TFT inference         │
                   │  · Daily 3-model ensemble             │
                   └───────────────────────────────────────┘
```

---

## 3. Microservices

8 FastAPI services. All share a common `backend/shared/` layer
(database, Redis, config, auth models, rate limiting, monitoring).

| Service | Port | Purpose | Key Endpoints |
|---|---|---|---|
| `api-gateway` | 8000 | Proxy all requests to internal services. Validates JWT, applies rate limit, strips trusted headers before re-injecting from auth state. | `/api/*` (proxies everything) |
| `auth-service` | 8001 | Registration, login, JWT refresh rotation, Google OAuth. Constant-time secret comparison (`hmac.compare_digest`). | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/google` |
| `market-data-service` | 8002 | Instruments, OHLCV history, financial metrics, earnings calendar, insider transactions. | `/instruments`, `/instruments/{t}/history`, `/earnings`, `/insider` |
| `news-service` | 8003 | RSS aggregation (Yahoo / Seeking Alpha / Reuters / MarketWatch), FinBERT sentiment classification, daily aggregates, Redis pub/sub for high-impact events. | `/news`, `/news/sentiment-summary` |
| `forecast-service` | 8004 | **Main ML path.** TFT inference (direct forward pass), batch forecast, rank endpoint, accuracy evaluation, alpha signals ensemble. | `POST /forecast/{t}`, `GET /top-picks`, `GET /alpha-signals`, `GET /forecast/{t}/rank` |
| `portfolio-service` | 8005 | User portfolios, positions with weighted average cost, transactions, watchlists, CSV export (Premium). | `/portfolios`, `/watchlists` |
| `notification-service` | 8006 | WebSocket via python-socketio (`main:socket_app`), price alerts, live-price fetcher (yfinance every 30s for subscribed tickers), circuit breaker. | `/socket.io/`, `/alerts` |
| `edgar-service` | 8007 | SEC EDGAR 10-K/10-Q XBRL parsing → income statements, balance sheets, cash flows. Pro+ only. | `/filings/{cik}`, `/statements/{t}` |

### Shared layer (`backend/shared/`)

```
shared/
├── database.py          # async SQLAlchemy 2.0 + asyncpg
├── redis_client.py      # aioredis singleton
├── config.py            # Pydantic Settings (env → typed config)
├── tier_limits.py       # Free/Pro/Premium quotas (single source of truth)
├── rate_limit.py        # Redis Lua script (atomic INCR+EXPIRE)
├── health.py            # Shared /health handler (DB + Redis)
├── monitoring.py        # Sentry + Prometheus metrics
├── utils.py             # HORIZON_STEPS, Q_* quantile constants, NaN sanitiser
└── models/              # SQLAlchemy ORM per schema
    ├── auth.py, market.py, news.py, forecast.py, portfolio.py, ...
```

---

## 4. Database Schema

9 schemas in PostgreSQL 15. Schema isolation allows per-service ownership
and simplifies migration planning.

### Schemas

| Schema | Purpose | Key tables |
|---|---|---|
| `auth` | Users, sessions, subscriptions | `users`, `refresh_tokens`, `subscriptions`, `oauth_accounts` |
| `market` | OHLCV, financials, macro | `instruments`, `price_history`, `financial_metrics`, `macro_history`, `company_profiles` |
| `edgar` | SEC filings | `filings`, `income_statements`, `balance_sheets`, `cash_flows` |
| `news` | Articles + sentiment | `articles`, `instrument_sentiment`, `social_mentions`, `sentiment_daily` |
| `forecast` | Model outputs | `forecasts`, `forecast_points`, `forecast_factors`, `forecast_history`, `model_versions`, `alpha_signals` |
| `portfolio` | User holdings | `portfolios`, `portfolio_items`, `transactions`, `watchlists`, `watchlist_items` |
| `earnings` | Earnings calendar | `earnings_calendar`, `earnings_results`, `eps_estimates` |
| `insider` | SEC Form 4 | `insider_transactions` |
| `notification` | Alerts | `alerts`, `alert_triggers`, `notification_log` |

### Key invariants

- Every table has `id` (UUID, PK), `created_at`, `updated_at`.
- Timestamps are `timestamptz` (UTC).
- FK constraints with `ON DELETE CASCADE` where child rows have no
  independent meaning (e.g. `forecast_points → forecasts`).
- Composite indexes on hot-path queries:
  - `price_history(ticker, date DESC)`
  - `forecasts(is_latest, ticker)` WHERE `is_latest = true`
  - `alerts(ticker, is_active, is_triggered)` — partial index for
    notification-service's price-poll hot loop.
- Unique constraints on natural keys: `earnings_results(ticker, report_date)`,
  `income_statements(ticker, period_end)`, `social_mentions(platform, post_id)`.

### Forecast tables in detail

```
model_versions
  ├── id (UUID, PK)
  ├── version (e.g. "tft-ensemble-ep2-ep4-ep5")
  ├── checkpoint_path
  ├── metrics (JSONB — raw back-test numbers for audit)
  └── is_active (only one active at a time)
             ▲
             │
forecasts    │
  ├── id, instrument_id, ticker, forecast_date
  ├── model_version_id ───────┘
  ├── current_close, signal (BUY/SELL/HOLD), confidence
  ├── predicted_return_{1d,1w,1m}
  ├── inference_time_s
  └── is_latest (bool — one per ticker; hot-path filter)
       ▲                     ▲
       │                     │
forecast_points         forecast_factors
  ├── forecast_id (FK) ───── ┘
  ├── step (0..21)         ├── forecast_id (FK)
  ├── horizon_label (1d/3d/...)  ├── factor_name
  ├── median, lower_80, upper_80 │
  └── lower_95, upper_95        ├── weight
                                 ├── direction (bullish/bearish)
                                 └── rank (1..10)

alpha_signals   (separate table, populated by ensemble script)
  ├── ticker, signal, confidence, confident_long
  ├── model_consensus (HIGH/MEDIUM/LOW)
  ├── disagreement_score
  ├── predicted_return_{1d,1w,1m}
  └── is_latest, expires_at
```

---

## 5. Data Flow

### 5.1 Real-time price flow

```
yfinance ──► update_prices.py (Airflow, every 15 min)
                │
                ├──► PostgreSQL market.price_history (INSERT ON CONFLICT UPDATE)
                ├──► Redis SET  mkt:price:{TICKER} (15-min TTL)
                └──► Redis PUBLISH price.updated
                                       │
                                       ▼
                            notification-service subscriber
                                       │
                                       ▼
                            Socket.IO emit to room "ticker:{TICKER}"
                                       │
                                       ▼
                            Frontend onPriceUpdate handler
```

In parallel, **notification-service live_price_fetcher** polls yfinance
every 30s for tickers with active WebSocket subscribers (zero subscribers
→ zero requests). Circuit breaker: 3 consecutive errors → 5-min pause.

### 5.2 Forecast flow (user-triggered)

```
User clicks "Refresh Forecast"
    │
    ▼  POST /api/forecast/{ticker}
gateway → forecast-service :8004
    │
    ▼
services/inference.py:run_inference(ticker, artifacts)
    │
    ├──► backfill_fresh_prices(ticker)   — 5-min TTL, sanity check
    ├──► backfill_fresh_macro()          — 5-min TTL
    ├──► build_feature_df(ticker)        — 82 rows × 107 features
    │    └──► _fetch_news_sentiment      — FinBERT on recent 30-day window
    ├──► TimeSeriesDataSet.from_parameters(...)
    ├──► model(x)                        — DIRECT forward pass, NOT .predict()
    ├──► quantiles (22, 7) → signal, CI, top factors
    │
    ▼
store_forecast(session, result)
    ├──► INSERT forecast.forecasts
    ├──► Bulk INSERT forecast_points
    └──► Bulk INSERT forecast_factors
    │
    ▼  Response to user (~10 s cold, ~3 s warm)
```

### 5.3 Batch forecast flow (Airflow cron)

```
Airflow dag_run_forecast (hourly, market hours)
    │
    ▼ waits for dag_fetch_prices + dag_fetch_news (ExternalTaskSensor)
    │
    ▼ triggers
POST http://forecast-service:8004/api/forecast/admin/run-batch
     (with INTERNAL_API_KEY header)
    │
    ▼
scripts/run_batch_forecast.py runs in background task
    │
    ▼ for ticker in valid_tickers (346):
    │    run_inference(ticker) → store_forecast()
    │
    ▼ on complete
Redis PUBLISH forecast.updated {success, failed, total}
    │
    ▼
notification-service subscriber → Socket.IO emit to "global" room
    │
    ▼
Frontend Dashboard refreshes Top Picks sidebar
```

### 5.4 Alpha Signals ensemble flow

```
Airflow dag_alpha_signals (daily, market close)
    │
    ▼ triggers
POST /api/forecast/admin/run-alpha-signals
    │
    ▼
scripts/run_alpha_signals.py
    ├──► artifacts.ensure_ensemble_loaded()  — loads ep2+ep4 (ep5 reused)
    │
    ▼ for ticker in valid_tickers:
    │    run_ensemble(ticker) →
    │       3x forward pass → average quantiles → disagreement score
    │       → INSERT alpha_signals
    │
    ▼ available via GET /api/forecast/alpha-signals
       (Pro/Premium gate — 403 for free tier)
```

---

## 6. Key Design Decisions

### 6.1 Why microservices over monolith?

- **Independent deployment** — bug fix in news service doesn't require
  redeploying the 1.5 GB forecast service.
- **Per-service dependency footprint** — forecast-service needs PyTorch
  (800 MB), auth-service needs only FastAPI + bcrypt.
- **Failure isolation** — yfinance rate-limit storms in market-data
  don't cascade to auth or portfolio.
- **Team boundary** — at scale, a dedicated ML team owns forecast-service
  while a product team owns portfolio / news.

Trade-off: cross-service latency (HTTPX calls), eventual consistency on
some reads, more Docker containers to manage.

### 6.2 Why direct forward pass instead of `Lightning.predict()`?

`pytorch_forecasting`'s `predict()` applies the `GroupNormalizer`'s
inverse transform, which hits NaN on live data outside the training
distribution (our test set ends 2026-04-02; current live date is after).
Direct `tft_model(x)` returns raw quantiles without the inverse, which
we apply ourselves (median unchanged; the normalizer was 'softplus',
which is essentially identity in the positive domain).

Without this workaround, forecasts for 60%+ of tickers come back as NaN.

### 6.3 Why a separate `alpha_signals` table?

Same model, different post-processing. Keeping alpha signals in their own
table lets us:
- Apply different retention policy (expires_at column).
- Add an `is_latest` flag that doesn't interfere with the main forecast
  hot path.
- Pro-gate the query at the DB level if needed.

### 6.4 Why Redis pub/sub for price updates?

WebSocket fan-out is awkward to do from the script that fetches prices
(different process, different language sometimes). Publishing to a Redis
channel decouples writers (Airflow python scripts) from subscribers
(notification-service) — any new subscriber just joins the channel.

### 6.5 Gateway strips trusted headers before re-injecting

```python
# gateway/middleware/jwt_auth.py
# Strip first, then inject. Otherwise an anonymous user could set
# X-User-Tier: premium in their curl and bypass paywalls.
for header in ("X-User-Id", "X-User-Tier", "X-Internal-Key"):
    request.headers.remove(header)
# ... validate JWT ...
request.headers["X-User-Id"] = str(user.id)
request.headers["X-User-Tier"] = user.tier
```

Internal services trust these headers (no duplicate JWT validation).

### 6.6 Radical-honesty metrics

UI publishes **live targets** (shrunk from back-test) as the primary
promise; raw back-test numbers live in tooltips. Rationale in
[`MODEL.md`](MODEL.md). Implementation: `frontend/src/lib/model-metrics.ts`
has `live_*` and `backtest_*` tiers; every surface is labelled explicitly.

---

## 7. Scaling Notes

At current scale (single-box local / single VPS):

- **Bottleneck:** forecast-service model loading (~1.5 GB RAM for 3 ckpts).
  Mitigation: lazy load ensemble (only on first Alpha Signals request).
- **Batch forecast throughput:** ~3 s per ticker warm → 346 tickers = ~20
  min. Acceptable for hourly cron.
- **WebSocket connections:** python-socketio with asyncio handles a few
  hundred concurrent clients easily.

Going to production scale:

1. **Horizontally scale non-ML services** (auth / market / news /
   portfolio / notification / edgar) — they're stateless FastAPI,
   put behind a load balancer.
2. **Keep forecast-service warm** (1–2 instances). Inference is the only
   CPU-heavy path. Consider a dedicated GPU instance for sub-second
   response time.
3. **Read replicas** for PostgreSQL — `forecast-service` read path
   (`/top-picks`, `/signals`) is 95% reads and can hit a replica.
4. **Split Airflow from the app cluster** — currently co-located for
   simplicity, but Airflow's DB churn is separate from the app's
   transactional load.

---

## 8. Deployment Topology (current)

Single docker-compose host running:

```
────────────────────────────────────────────────────
Docker host
├─ postgres:5432             (15)
├─ redis:6379                (7)
├─ api-gateway:8000
├─ auth-service:8001
├─ market-data-service:8002
├─ news-service:8003
├─ forecast-service:8004    (main ML path, ~1.5 GB RAM)
├─ portfolio-service:8005
├─ notification-service:8006
├─ edgar-service:8007
├─ airflow-webserver:8080
├─ airflow-scheduler
├─ pgadmin:5050             (optional)
└─ frontend (next start:3000)  — run outside compose for dev convenience
────────────────────────────────────────────────────
```

---

## 9. References

- **Setup:** [`SETUP.md`](SETUP.md)
- **ML model:** [`MODEL.md`](MODEL.md)
- **API:** [`BACKEND_API.md`](BACKEND_API.md)
- **Internal notes:** `ENSEMBLE_NOTES.md`, `CLAUDE.md`, `PLAN.md`
