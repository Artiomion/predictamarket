# PredictaMarket

AI-powered stock prediction platform for S&P 500. Multimodal ML model (Temporal Fusion Transformer, 107 features) ranks stocks by predicted return with 99.5% win rate on confident signals.

## Architecture

```
Frontend (Next.js :3000)
    ↓
API Gateway (:8000) — JWT, rate limiting, CORS, request tracing
    ↓
┌─────────────┬─────────────┬──────────────┬──────────────┐
│ Auth :8001  │ Market :8002│ News :8003   │ Forecast:8004│
│ JWT, OAuth  │ OHLCV, fin  │ RSS, FinBERT │ TFT model    │
├─────────────┼─────────────┼──────────────┼──────────────┤
│Portfolio:8005│ Notif :8006 │ EDGAR :8007  │              │
│ P&L, watch  │ WS, alerts  │ SEC filings  │              │
└─────────────┴─────────────┴──────────────┴──────────────┘
    ↓               ↓
PostgreSQL 15    Redis 7 (cache + pub/sub)
```

## Quick Start

```bash
# 1. Clone and setup
cp .env.example .env  # Fill in secrets

# 2. Start infrastructure
docker compose up -d postgres redis pgadmin

# 3. Initialize database (33 tables, 9 schemas)
docker compose exec postgres psql -U postgres -d predictamarket -f /docker-entrypoint-initdb.d/init.sql

# 4. Start backend services
docker compose up -d api-gateway auth-service market-data-service

# 5. Seed data (94 S&P 500 tickers + 5y prices)
PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/seed_instruments.py

# 6. Run tests
.venv/bin/pytest tests/test_unit.py -v          # 22 unit tests (no infra)
.venv/bin/pytest tests/test_step3_auth.py -v    # 12 auth tests
```

## Services

| Service | Port | Endpoints | Key Features |
|---------|------|-----------|--------------|
| api-gateway | 8000 | Proxy all | JWT validation, rate limiting (60/300/1000 rpm), CORS, request-id |
| auth-service | 8001 | 8 | Register, login, Google OAuth, JWT refresh rotation, bcrypt |
| market-data-service | 8002 | 8 | Instruments, OHLCV history, financials, earnings, insider |
| news-service | 8003 | 4 | RSS aggregation, FinBERT sentiment, Redis pub/sub |
| forecast-service | 8004 | 8 | Real TFT inference (~8s), top picks, signals, batch |
| portfolio-service | 8005 | 15 | Portfolios, positions (weighted avg), watchlists, CSV export |
| notification-service | 8006 | 4 | WebSocket (Socket.IO), price alerts, email notifications |
| edgar-service | 8007 | 4 | SEC EDGAR XBRL parsing, income/balance/cashflow |

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, asyncpg
- **ML:** PyTorch, pytorch-forecasting (TFT), FinBERT, scikit-learn (PCA)
- **Database:** PostgreSQL 15 (9 schemas, 33 tables)
- **Cache:** Redis 7 (rate limiting, pub/sub, price cache)
- **Auth:** JWT (python-jose), bcrypt, Google OAuth
- **WebSocket:** python-socketio
- **Monitoring:** Sentry, Prometheus metrics
- **CI/CD:** GitHub Actions
- **Container:** Docker Compose

## Environment Variables

```bash
# Required
JWT_SECRET=           # openssl rand -hex 32
INTERNAL_API_KEY=     # openssl rand -hex 32
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/predictamarket
REDIS_URL=redis://localhost:6379/0

# Optional
GOOGLE_CLIENT_ID=     # Google OAuth
GOOGLE_CLIENT_SECRET=
FRED_API_KEY=         # FRED macro data
SENTRY_DSN=           # Error tracking
EMAIL_ENABLED=false   # SendGrid or SMTP
SENDGRID_API_KEY=
```

## Testing

```bash
# Unit tests (no infrastructure needed, <1s)
pytest tests/test_unit.py -v

# Integration tests (requires Docker services running)
pytest tests/ -v --ignore=tests/test_unit.py

# Full suite: 174 tests (22 unit + 152 integration)
```

## Data Pipeline

```bash
# Seed 94 S&P 500 instruments + 5y OHLCV
python backend/market-data-service/scripts/seed_instruments.py

# Update scripts (run via cron or Airflow)
python backend/market-data-service/scripts/update_prices.py
python backend/market-data-service/scripts/update_financials.py
python backend/market-data-service/scripts/update_earnings.py
python backend/market-data-service/scripts/update_insider.py
python backend/news-service/scripts/fetch_news.py
python backend/edgar-service/scripts/fetch_edgar.py
python backend/forecast-service/scripts/run_batch_forecast.py
```

## ML Model

- **Architecture:** Temporal Fusion Transformer (16.3M params)
- **Input:** 107 features (OHLCV, technicals, macro, FinBERT sentiment, SEC financials)
- **Output:** 7 quantiles × 22 trading days (1 month forecast)
- **Metrics:** MAPE 6.1%, Win Rate 99.5% (confident signals), Top-20 Return 77.7%

## License

Proprietary. All rights reserved.
