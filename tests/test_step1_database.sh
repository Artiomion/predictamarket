#!/bin/bash
set -euo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
DOCKER="/usr/local/bin/docker"
COMPOSE="$DOCKER compose"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PASSED=0
FAILED=0
RESULTS=()

pass() { PASSED=$((PASSED+1)); RESULTS+=("PASSED: $1"); echo "✅ PASSED: $1"; }
fail() { FAILED=$((FAILED+1)); RESULTS+=("FAILED: $1 — $2"); echo "❌ FAILED: $1 — $2"; }

PSQL="$COMPOSE exec -T postgres psql -U postgres -d predictamarket -t -A"

# ============================================================================
# ТЕСТ 1 — Docker запускается
# ============================================================================
echo ""
echo "========== ТЕСТ 1: Docker containers running =========="
$COMPOSE up -d postgres redis pgadmin 2>&1 | tail -5
sleep 5

RUNNING_CONTAINERS=$($COMPOSE ps --status running --format '{{.Name}}' 2>/dev/null | sort)
ALL_OK=true
for SVC in postgres redis pgadmin; do
  if echo "$RUNNING_CONTAINERS" | grep -q "$SVC"; then
    echo "  $SVC: running"
  else
    echo "  $SVC: NOT running"
    ALL_OK=false
  fi
done
if $ALL_OK; then pass "TEST 1 — All containers running"; else fail "TEST 1 — Docker containers" "not all running"; fi

# ============================================================================
# ТЕСТ 2 — Все 9 схем существуют
# ============================================================================
echo ""
echo "========== ТЕСТ 2: All 9 schemas exist =========="
EXPECTED_SCHEMAS="auth earnings edgar forecast insider market news notification portfolio"
ACTUAL_SCHEMAS=$($PSQL -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast','public') ORDER BY schema_name;" | tr '\n' ' ' | xargs)
echo "  Expected: $EXPECTED_SCHEMAS"
echo "  Actual:   $ACTUAL_SCHEMAS"
if [ "$ACTUAL_SCHEMAS" = "$EXPECTED_SCHEMAS" ]; then
  pass "TEST 2 — All 9 schemas exist"
else
  fail "TEST 2 — Schemas" "missing or extra schemas"
fi

# ============================================================================
# ТЕСТ 3 — Ключевые таблицы во всех схемах
# ============================================================================
echo ""
echo "========== ТЕСТ 3: Key tables in all schemas =========="

check_tables() {
  local schema="$1"
  shift
  local expected="$@"
  local actual
  actual=$($PSQL -c "SELECT tablename FROM pg_tables WHERE schemaname='$schema' ORDER BY tablename;" | tr '\n' ' ' | xargs)
  local missing=""
  for tbl in $expected; do
    if ! echo " $actual " | grep -q " $tbl "; then
      missing="$missing $tbl"
    fi
  done
  if [ -z "$missing" ]; then
    echo "  $schema: OK ($(echo $expected | wc -w | xargs) tables)"
    return 0
  else
    echo "  $schema: MISSING:$missing"
    return 1
  fi
}

TEST3_OK=true
check_tables auth users refresh_tokens subscriptions oauth_accounts || TEST3_OK=false
check_tables market instruments price_history financial_metrics company_profiles || TEST3_OK=false
check_tables edgar filings income_statements balance_sheets cash_flows || TEST3_OK=false
check_tables news articles instrument_sentiment social_mentions sentiment_daily || TEST3_OK=false
check_tables forecast forecasts forecast_points forecast_factors model_versions forecast_history || TEST3_OK=false
check_tables portfolio portfolios portfolio_items transactions watchlists watchlist_items || TEST3_OK=false
check_tables earnings earnings_calendar earnings_results eps_estimates || TEST3_OK=false
check_tables insider insider_transactions || TEST3_OK=false
check_tables notification alerts alert_triggers notification_log || TEST3_OK=false
if $TEST3_OK; then pass "TEST 3 — All tables present"; else fail "TEST 3 — Tables" "missing tables"; fi

# ============================================================================
# ТЕСТ 4 — Структура auth.users корректна
# ============================================================================
echo ""
echo "========== ТЕСТ 4: auth.users structure =========="
COLUMNS=$($PSQL -c "SELECT column_name FROM information_schema.columns WHERE table_schema='auth' AND table_name='users' ORDER BY ordinal_position;")
echo "  Columns: $(echo $COLUMNS | tr '\n' ', ')"

REQUIRED_COLS="id email password_hash tier is_active created_at updated_at deleted_at"
TEST4_OK=true
for col in $REQUIRED_COLS; do
  if ! echo "$COLUMNS" | grep -q "^${col}$"; then
    echo "  MISSING column: $col"
    TEST4_OK=false
  fi
done

# Check id is UUID
ID_TYPE=$($PSQL -c "SELECT data_type FROM information_schema.columns WHERE table_schema='auth' AND table_name='users' AND column_name='id';")
if [ "$ID_TYPE" != "uuid" ]; then
  echo "  id type is '$ID_TYPE', expected 'uuid'"
  TEST4_OK=false
else
  echo "  id type: uuid ✓"
fi

# Check timestamps are timestamptz
for ts_col in created_at updated_at deleted_at; do
  TS_TYPE=$($PSQL -c "SELECT data_type FROM information_schema.columns WHERE table_schema='auth' AND table_name='users' AND column_name='$ts_col';" | xargs)
  if [ "$TS_TYPE" = "timestamp with time zone" ]; then
    echo "  $ts_col: timestamptz ✓"
  else
    echo "  $ts_col: '$TS_TYPE' (expected timestamptz)"
    TEST4_OK=false
  fi
done

if $TEST4_OK; then pass "TEST 4 — auth.users structure correct"; else fail "TEST 4 — auth.users" "structure mismatch"; fi

# ============================================================================
# ТЕСТ 5 — Индексы созданы
# ============================================================================
echo ""
echo "========== ТЕСТ 5: Indexes exist =========="
INDEX_COUNT=$($PSQL -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname IN ('auth','market','forecast','portfolio','news','edgar','earnings','insider','notification');")
echo "  Total indexes: $INDEX_COUNT"

TEST5_OK=true
check_index() {
  local schema="$1" idx="$2"
  local exists
  exists=$($PSQL -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='$schema' AND indexname='$idx';")
  if [ "$exists" = "1" ]; then
    echo "  $idx: ✓"
    return 0
  else
    echo "  $idx: MISSING"
    return 1
  fi
}

check_index auth idx_auth_users_email || TEST5_OK=false
check_index market idx_market_instruments_ticker || TEST5_OK=false
check_index market idx_market_price_ticker || TEST5_OK=false
check_index market idx_market_price_date || TEST5_OK=false
check_index forecast idx_forecast_ticker || TEST5_OK=false
check_index forecast idx_forecast_date || TEST5_OK=false
check_index portfolio idx_portfolio_user || TEST5_OK=false
check_index news idx_news_articles_published || TEST5_OK=false
check_index insider idx_insider_ticker || TEST5_OK=false
check_index earnings idx_earnings_cal_ticker || TEST5_OK=false
check_index notification idx_notification_alerts_user || TEST5_OK=false

if $TEST5_OK; then pass "TEST 5 — Key indexes exist"; else fail "TEST 5 — Indexes" "missing indexes"; fi

# ============================================================================
# ТЕСТ 6 — SQLAlchemy подключается
# ============================================================================
echo ""
echo "========== ТЕСТ 6: SQLAlchemy connects =========="
SA_OUTPUT=$(cd "$PROJECT_ROOT" && PYTHONPATH=. .venv/bin/python -c "
import asyncio, os
os.environ['DEBUG'] = 'false'
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/predictamarket', echo=False)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test():
    async with session_factory() as session:
        result = await session.execute(text('SELECT 1'))
        print('DB OK:', result.scalar())
    await engine.dispose()

asyncio.run(test())
" 2>&1 | grep "DB OK" || echo "")

echo "  Output: $SA_OUTPUT"
if echo "$SA_OUTPUT" | grep -q "DB OK: 1"; then
  pass "TEST 6 — SQLAlchemy connects"
else
  fail "TEST 6 — SQLAlchemy" "connection failed"
fi

# ============================================================================
# ТЕСТ 7 — Redis подключается
# ============================================================================
echo ""
echo "========== ТЕСТ 7: Redis connects =========="
REDIS_OUTPUT=$(cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_ROOT/backend" .venv/bin/python -c "
import asyncio
from shared.redis_client import get_redis

async def test():
    r = await get_redis()
    await r.set('test_key', 'ok', ex=10)
    val = await r.get('test_key')
    print('Redis OK:', val)
    await r.aclose()

asyncio.run(test())
" 2>&1 | grep "Redis OK" || echo "")

echo "  Output: $REDIS_OUTPUT"
if echo "$REDIS_OUTPUT" | grep -q "Redis OK: ok"; then
  pass "TEST 7 — Redis connects"
else
  fail "TEST 7 — Redis" "connection failed"
fi

# ============================================================================
# ИТОГИ
# ============================================================================
echo ""
echo "============================================"
echo "  RESULTS: $PASSED passed, $FAILED failed"
echo "============================================"
for r in "${RESULTS[@]}"; do
  echo "  $r"
done
echo ""

if [ $FAILED -gt 0 ]; then exit 1; fi
