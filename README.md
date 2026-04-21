# PredictaMarket

AI-powered stock-prediction platform for the S&P 500. A Temporal Fusion
Transformer (3-model ensemble, 107 features) ranks **346 tickers** by
predicted 1-month return and exposes the rankings through a Next.js
dashboard and a Pro-gated Alpha Signals feed.

**Live targets** (what we promise, honest about degradation from back-test):

| Metric                        | Target           |
|-------------------------------|------------------|
| Top-20 Sharpe                 | **~1.0**         |
| Consensus BUY Sharpe          | **~1.3**         |
| Consensus win rate            | **~55%**         |
| 22-day directional accuracy   | **~60%**         |
| Alpha vs S&P 500              | **~+4 pp**       |

Raw back-test numbers are higher (Sharpe 1.45 / 8.15, WR 63% on 27 trades)
but reflect a single 23-day hold-out — we shrink them for realism. Full
methodology in [`docs/MODEL.md`](docs/MODEL.md).

---

## Quick Start

**Prerequisites:** Docker Desktop, Node 20+, Python 3.12, ~8 GB free RAM,
~2 GB disk for model checkpoints.

```bash
# 1. Clone + env
git clone <repo> && cd PredictaMarket
cp .env.example .env
# Edit .env — set JWT_SECRET and INTERNAL_API_KEY:
#   openssl rand -hex 32
# Also set FINNHUB_API_KEY for live charts (free tier from finnhub.io).

# 2. Pull model checkpoints (~1.2 GB, gitignored)
#    Place in models/ directory:
#      tft-epoch=02-val_loss=8.8051.ckpt
#      tft-epoch=04-val_loss=9.2586.ckpt
#      tft-epoch=05-val_loss=9.3008.ckpt
#    (Other artifacts — config.json, training_dataset_params.pkl,
#     pca_model.pkl, old_model_sp500_tickers.txt — are in the repo.)

# 3. Start the full stack
docker compose up -d

# 4. Start the frontend
cd frontend
npm install
npm run build
npm run start    # production mode on :3000
```

Open **http://localhost:3000** — register a free account, navigate to
**/stocks/AAPL → Forecast tab**, and you should see a fresh TFT prediction
in ~10 s.

> **Detailed setup, env vars, troubleshooting:** [`docs/SETUP.md`](docs/SETUP.md)

---

## Project Layout

```
predictamarket/
├── backend/                 # 8 FastAPI microservices + shared layer
│   ├── shared/              # DB, Redis, auth, rate-limit, models
│   ├── api-gateway/         # :8000 — proxy, JWT, rate limit
│   ├── auth-service/        # :8001 — JWT + Google OAuth
│   ├── market-data-service/ # :8002 — OHLCV, financials, earnings
│   ├── news-service/        # :8003 — RSS + FinBERT sentiment
│   ├── forecast-service/    # :8004 — TFT inference (main ML path)
│   ├── portfolio-service/   # :8005 — portfolios, watchlists
│   ├── notification-service/# :8006 — WebSocket + alerts
│   └── edgar-service/       # :8007 — SEC EDGAR XBRL
│
├── frontend/                # Next.js 14 + TypeScript
│   └── src/
│       ├── app/             # App Router routes
│       ├── components/      # UI + features + layout + charts
│       ├── lib/             # api, hooks, model-metrics.ts (SSOT)
│       └── store/           # Zustand
│
├── models/                  # TFT checkpoints + config (.ckpt in .gitignore)
├── airflow/dags/            # 13 scheduled DAGs (prices, news, forecast)
├── docker/postgres/init.sql # 9 schemas, 33+ tables, indexes
├── docker-compose.yml
│
└── docs/                    # Documentation (this directory)
    ├── SETUP.md             # Full install + run guide
    ├── ARCHITECTURE.md      # System design + data flow
    ├── MODEL.md             # TFT architecture + training + test metrics
    ├── BACKEND_API.md       # API reference (66 endpoints)
    └── ENSEMBLE_NOTES.md    # Internal ensemble study notes
```

---

## How It Works (60 seconds)

```
                User
                 │
                 ▼
  ┌──────────────────────────────────┐
  │  Next.js (:3000)                 │  Dashboard · Top Picks · Alpha Signals
  └──────────────┬───────────────────┘  · /stocks/[ticker] · Portfolio
                 │
                 ▼
  ┌──────────────────────────────────┐
  │  API Gateway (:8000)             │  JWT validation, rate limit, CORS
  └──────────────┬───────────────────┘
                 │
       ┌─────────┼──────────┬──────────┬──────────┐
       ▼         ▼          ▼          ▼          ▼
   auth     market     news        forecast    portfolio
   :8001    :8002      :8003       :8004       :8005   …and 3 more
                                     │
                                     ▼
             ┌──────────────────────────────┐
             │  TFT Ensemble (ep2+ep4+ep5)  │  ep5 primary (single-model Top Picks)
             │  16.3M params, 107 features  │  ep2+ep4+ep5 ensemble (Alpha Signals)
             └──────────────┬───────────────┘
                            │
                            ▼
              ┌──────────────────────────────┐
              │  PostgreSQL 15 + Redis 7     │
              │  9 schemas · pub/sub events  │
              └──────────────────────────────┘
                            ▲
                            │ (every 15 min / 30 min / hourly cron)
                            │
              ┌──────────────────────────────┐
              │  Airflow (:8080)             │  13 DAGs: prices, macro, news,
              │  — yfinance · RSS · FRED     │  forecasts, earnings, EDGAR, …
              │  — FinBERT · SEC             │
              └──────────────────────────────┘
```

- **Free user** hits `GET /api/forecast/top-picks` → reads from
  `forecast.forecasts` (populated hourly by `dag_run_forecast` using ep5).
- **Pro user** hits `GET /api/forecast/alpha-signals` → reads from
  `forecast.alpha_signals` (populated daily by `dag_alpha_signals` using the
  3-model ensemble with consensus filter).
- **Per-ticker** page calls `POST /api/forecast/{ticker}` → on-demand
  inference (~10 s cold, ~3 s warm) using ep5, stored in DB for future
  reads.

---

## Services Overview

| Service | Port | Health | Rate limit (Free/Pro/Premium) |
|---|---|---|---|
| api-gateway         | 8000 | `/health` | 60 / 300 / 1000 rpm |
| auth-service        | 8001 | `/health` | N/A |
| market-data-service | 8002 | `/health` | via gateway |
| news-service        | 8003 | `/health` | via gateway |
| forecast-service    | 8004 | `/health` | 1 / 10 / unlimited forecasts/day |
| portfolio-service   | 8005 | `/health` | via gateway |
| notification-service | 8006 | `/socket.io/` | via gateway |
| edgar-service       | 8007 | `/health` | Pro+ only |

Auxiliary: PostgreSQL :5432, Redis :6379, Airflow :8080, pgAdmin :5050.

Full API reference: [`docs/BACKEND_API.md`](docs/BACKEND_API.md)

---

## Key Design Decisions

- **Microservices** so each domain (market data, news, forecast, portfolio)
  can scale independently and have its own dependency footprint.
- **TFT direct forward pass** (not `Lightning.predict()`) — `predict()`
  applies GroupNormalizer inverse transform which produces NaN on
  out-of-distribution live data.
- **3-tier pricing gate** on Alpha Signals — the consensus filter is the
  main value-prop for Pro ($15/mo); Top Picks (Free/Pro) uses the single
  primary model.
- **Radical-honesty metrics** — UI publishes *live targets* (shrunk from
  back-test) not raw back-test numbers. Back-test values live only in
  tooltips and audit footers. Rationale: [`docs/MODEL.md`](docs/MODEL.md).
- **Progressive disclosure** via `<PageGuide>` — every page has a
  collapsed "New to this page?" panel with plain-English explanation,
  how-to-use-for-trading instructions, and a glossary.

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 async, asyncpg,
  python-socketio, structlog, Sentry, Prometheus
- **ML:** PyTorch 2.6, pytorch-forecasting 1.1.1, Lightning 2.5,
  transformers (FinBERT), scikit-learn (IncrementalPCA)
- **Data:** PostgreSQL 15, Redis 7, Airflow 2.x
- **Frontend:** Next.js 14 (App Router), TypeScript strict, Tailwind CSS,
  Framer Motion, TradingView Lightweight Charts, Zustand, shadcn/ui
- **Auth:** JWT (python-jose), bcrypt, Google OAuth, Finnhub (real-time prices)
- **Infra:** Docker Compose, GitHub Actions, optional Sentry

---

## Documentation Index

| Doc | Audience | What it covers |
|---|---|---|
| [`docs/SETUP.md`](docs/SETUP.md) | Operators | Full install, env vars, running each service, troubleshooting |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Engineers | All services, DB schema, data flow, scaling notes |
| [`docs/MODEL.md`](docs/MODEL.md) | ML engineers / investors | TFT architecture, training, test metrics, live vs back-test |
| [`docs/BACKEND_API.md`](docs/BACKEND_API.md) | Frontend devs | 66 endpoints, schemas, WebSocket events, rate limits |
| `CLAUDE.md` | Claude Code sessions | Project context, conventions, caveats |
| `PLAN.md` | Product | Full spec, screens, DB schemas, roadmap |

---

## License

Proprietary. All rights reserved.
