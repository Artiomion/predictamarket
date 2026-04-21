# Setup Guide

Complete installation and operational guide for PredictaMarket.

**Expected time:** 20–30 minutes for a fresh install.

**Audience:** developer or ops person deploying the platform locally or to a
single VPS.

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker Desktop | 24+ | Compose v2 (comes bundled) |
| Node.js | 20+ | For the Next.js frontend |
| Python | 3.12 | Backend uses async features unavailable in 3.11 |
| git | 2+ | Standard |
| Disk | ~4 GB free | ~1.2 GB for model checkpoints, ~1 GB Docker images, ~1 GB DB |
| RAM | ~8 GB free | Forecast service alone uses ~1.5 GB (model in memory) |

**Optional but recommended:**

- **Finnhub API key** (free tier at <https://finnhub.io>) — needed for live
  candlestick charts on the ticker page. Without it the Chart tab
  degrades gracefully but shows no real-time updates.
- **FRED API key** (free at <https://fred.stlouisfed.org/docs/api/api_key.html>) —
  for CPI / unemployment / fed-funds macro features. Without it those
  columns get zero-filled and the model's macro signal degrades.

---

## 2. Clone and Configure

```bash
git clone <repo-url> PredictaMarket
cd PredictaMarket
cp .env.example .env
```

Edit `.env` — the critical fields are:

```bash
# ── Secrets (REQUIRED) ─────────────────────────────────────────
JWT_SECRET=<generate: openssl rand -hex 32>
INTERNAL_API_KEY=<generate: openssl rand -hex 32>

# ── Database (defaults work for Docker Compose) ────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/predictamarket
REDIS_URL=redis://localhost:6379/0

# ── External APIs (recommended) ────────────────────────────────
FINNHUB_API_KEY=<from finnhub.io>     # live charts
FRED_API_KEY=<from fred.stlouisfed.org> # macro features

# ── OAuth (optional) ───────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ── Payments (optional) ────────────────────────────────────────
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# ── Monitoring (optional) ──────────────────────────────────────
SENTRY_DSN=
```

**JWT_SECRET validation:** `shared/config.py` refuses to start if the secret
contains `change-me`, `placeholder`, or `replace-me`, or is shorter than 16
characters. This is intentional — weak secrets break in production.

---

## 3. Model Checkpoints

The three production TFT checkpoints (~188 MB each, 564 MB total) are in
`.gitignore` — you have to obtain them out-of-band.

Place these three files in `models/`:

```
models/
├── tft-epoch=02-val_loss=8.8051.ckpt    # ensemble member
├── tft-epoch=04-val_loss=9.2586.ckpt    # ensemble member
└── tft-epoch=05-val_loss=9.3008.ckpt    # primary (single-model)
```

**SHA256 hashes** (verified on load; mismatch logs a warning but does NOT
block startup — useful for dev environments with different checkpoints):

```
tft-epoch=02: 55eeafea8fc92e1c44e4bee9cf7ac0fe431bcdf0cb8a35b2c62ae93a8e5cb126
tft-epoch=04: b9ea9c7e6098a8745c9eb3252e9aa2bd14b8ccb8c53fa350fb924fbbcf95010f
tft-epoch=05: ae103556b1fb1f5fbf5fd10c27b935b2e4f691bc0d5bc0afe0c6741e51d7330f
```

The non-checkpoint artifacts are already in the repo:

```
models/
├── config.json                          # 107 features, cutoffs, tickers
├── training_dataset_params.pkl          # GroupNormalizer, encoders
├── pca_model.pkl                        # IncrementalPCA(n=32) for FinBERT
└── old_model_sp500_tickers.txt          # 346 S&P 500 tickers (the universe)
```

---

## 4. Start the Backend

```bash
docker compose up -d
```

This spins up:

- **postgres** (:5432) — runs `docker/postgres/init.sql` on first start →
  9 schemas, 33+ tables
- **redis** (:6379)
- **pgadmin** (:5050) — optional web UI for the DB
- **airflow-webserver** (:8080) + **airflow-scheduler** — 13 DAGs
- **8 microservices** on :8000–:8007

Wait ~30 seconds for the first-start initialization (model loading happens
lazily on first forecast request, not at startup).

**Verify health:**

```bash
curl -s http://localhost:8000/health | jq
# → {"status":"ok","service":"api-gateway","redis":"ok"}

for port in 8001 8002 8003 8004 8005 8006 8007; do
  curl -s -o /dev/null -w "localhost:$port → %{http_code}\n" http://localhost:$port/health
done
```

All should return `200`. Docker Compose may report `(unhealthy)` because
healthcheck command differs from the real HTTP endpoint — that's cosmetic;
the services are fine as long as `/health` returns 200.

---

## 5. Start the Frontend

```bash
cd frontend
npm install
npm run build
npm run start    # production mode (recommended for local ops)
#   → Ready on http://localhost:3000
```

For development:

```bash
npm run dev      # hot-reload on :3000
```

---

## 6. Seed Data

The database starts empty. Populate it in this order:

### Option A: Trigger the Airflow DAGs (recommended)

Open <http://localhost:8080>, log in with `predictamarket / predictamarket`,
then click the **Trigger** button on each DAG in this order:

1. `dag_fetch_prices` — OHLCV for all 346 tickers (~5 min)
2. `dag_fetch_macro` — VIX, S&P 500, DXY, gold, oil (~1 min)
3. `dag_fetch_fred` — CPI, unemployment, fed funds (~1 min)
4. `dag_fetch_news` — RSS + FinBERT sentiment (~10 min)
5. `dag_fetch_earnings` — earnings calendar (~2 min)
6. `dag_fetch_insider` — insider transactions (~3 min)
7. `dag_fetch_financials` — SEC 10-K/10-Q (~15 min)
8. `dag_fetch_edgar` — XBRL parsed statements (~20 min)
9. `dag_run_forecast` — TFT inference for all 346 tickers (~10 min)
10. `dag_alpha_signals` — 3-model ensemble inference (~20 min)

Once finished, http://localhost:3000 will show real data on every page.

### Option B: Via backend admin endpoints

```bash
KEY="$(grep INTERNAL_API_KEY .env | cut -d= -f2)"

# Kick off batch forecast + alpha signals directly
curl -X POST http://localhost:8004/api/forecast/admin/run-batch \
  -H "x-internal-key: $KEY"

curl -X POST http://localhost:8004/api/forecast/admin/run-alpha-signals \
  -H "x-internal-key: $KEY"
```

---

## 7. Create a Test User

```bash
# Register via the gateway
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!","name":"Test"}'
```

Response includes `access_token`, `refresh_token`, and `user_id`.

Log in at <http://localhost:3000/auth/login>.

**Upgrade to Pro tier** (for Alpha Signals):

```bash
docker compose exec postgres psql -U postgres -d predictamarket -c \
  "UPDATE auth.users SET tier='pro' WHERE email='test@example.com';"
```

---

## 8. Verify End-to-End

1. Open **http://localhost:3000** — landing should show live targets
   (~1.0 Sharpe, ~55% WR) in the Performance section.
2. **Sign in → Dashboard** — ModelStrengthBanner + Top Picks sidebar
   populated with real tickers.
3. **Top Picks page** — list of BUY-tier stocks with positive predicted
   returns, sorted by 1m return DESC.
4. **Click any ticker → Forecast tab** — live inference runs (~10 s),
   shows median / 80% CI / 95% CI / rank position.
5. **Alpha Signals (Pro only)** — filtered feed of consensus BUY signals.

If any of these are empty, re-check that `dag_run_forecast` and
`dag_alpha_signals` completed successfully in Airflow.

---

## 9. Operational Commands

### Daily ops

```bash
# Check service status
docker compose ps

# Tail logs for a service
docker compose logs -f forecast-service

# Restart a single service (no downtime for others)
docker compose restart forecast-service

# Restart frontend (if running via npm, not in Docker)
cd frontend && pkill -9 -f next-server && npm run start &
```

### Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d predictamarket

# Backup
docker compose exec postgres pg_dump -U postgres predictamarket > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U postgres -d predictamarket
```

### Redis

```bash
# Connect
docker compose exec redis redis-cli

# Clear all (careful — wipes rate-limit counters, pub/sub state, price cache)
docker compose exec redis redis-cli FLUSHALL
```

### Airflow

```bash
# CLI inside the scheduler container
docker compose exec airflow-scheduler bash

airflow dags list                                 # list all DAGs
airflow dags trigger dag_run_forecast             # trigger a DAG
airflow tasks list dag_run_forecast               # inspect tasks
airflow dags state dag_run_forecast 2026-04-21    # state for a date
```

---

## 10. Troubleshooting

### Forecast returns 500

Check `forecast-service` logs:

```bash
docker compose logs forecast-service --tail=100
```

Common causes:
- **Missing checkpoint** — `primary_ckpt_missing` warning in log.
  Verify `models/tft-epoch=05-val_loss=9.3008.ckpt` exists and the
  `MODELS_DIR` env var points to `/models` inside the container.
- **Not enough price history** — the service needs ≥60 rows of OHLCV
  per ticker. If you just ran seed, wait for `dag_fetch_prices` to fully
  populate.
- **yfinance rate limit** — the backfill step will log
  `backfill_rejected_extreme_delta` or `backfill_prices_skipped`. Retry
  in a few minutes; the TTL cache clears after 5 min.

### "Signal expired" or stale forecasts

Trigger `dag_run_forecast` manually in Airflow, or use the admin
endpoint:

```bash
curl -X POST http://localhost:8004/api/forecast/admin/run-batch \
  -H "x-internal-key: $INTERNAL_API_KEY"
```

### WebSocket on :8006 not connecting

`notification-service` must be started with `main:socket_app`, NOT
`main:app` — Socket.IO requires a separate ASGI app. Check
`docker-compose.yml` uvicorn command for that service.

### "Unhealthy" in `docker compose ps`

Almost always cosmetic — the healthcheck command uses a path or
timeout that doesn't quite match. Verify by `curl`ing the service
directly on its port:

```bash
curl -s http://localhost:8004/health
# → {"status":"ok"}
```

If that works, the service is fine.

### Frontend "Failed to fetch" on all pages

Usually a JWT issue. Clear localStorage and re-login:

```javascript
// In browser DevTools console
localStorage.clear()
location.href = '/auth/login'
```

Or the gateway is down — `curl http://localhost:8000/health`.

### Running out of memory

The forecast-service loads all three TFT checkpoints into RAM when Alpha
Signals runs (3 × ~188 MB + activations ≈ 1.5 GB). Add swap or increase
the Docker Desktop memory limit.

---

## 11. Stopping Everything

```bash
# Stop services, keep data
docker compose down

# Stop + wipe databases (careful — destroys all user data)
docker compose down -v

# Stop the frontend (if running outside Docker)
pkill -9 -f next-server
```

---

## Next Steps

- **Architecture deep-dive:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **ML model internals:** [`MODEL.md`](MODEL.md)
- **API reference:** [`BACKEND_API.md`](BACKEND_API.md)
