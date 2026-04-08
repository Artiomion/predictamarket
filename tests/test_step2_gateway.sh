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

pass() { PASSED=$((PASSED+1)); RESULTS+=("PASSED: $1"); echo "PASSED: $1"; }
fail() { FAILED=$((FAILED+1)); RESULTS+=("FAILED: $1 — $2"); echo "FAILED: $1 — $2"; }

# Ensure gateway is running
$COMPOSE up -d api-gateway 2>&1 | tail -3
sleep 3

# ============================================================================
# TEST 1 — Health check
# ============================================================================
echo ""
echo "========== TEST 1: Health check =========="
BODY=$(curl -s localhost:8000/health)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" localhost:8000/health)
echo "  Status: $STATUS, Body: $BODY"
if [ "$STATUS" = "200" ] && echo "$BODY" | grep -q '"status":"ok"'; then
  pass "TEST 1 — Health check"
else
  fail "TEST 1 — Health check" "status=$STATUS body=$BODY"
fi

# ============================================================================
# TEST 2 — Public routes without token
# ============================================================================
echo ""
echo "========== TEST 2: Public routes without token =========="
TEST2_OK=true
# Gateway 401 body contains "Missing or invalid Authorization header"
# Upstream 401 (e.g. wrong password) is fine — it means the gateway let the request through
GATEWAY_401="Missing or invalid Authorization header"

check_public() {
  local method="$1" url="$2" data="$3" label="$4"
  local body status
  if [ "$method" = "POST" ]; then
    body=$(curl -s -w "\n%{http_code}" -X POST "localhost:8000$url" -H "Content-Type: application/json" -d "$data")
  else
    body=$(curl -s -w "\n%{http_code}" "localhost:8000$url")
  fi
  status=$(echo "$body" | tail -1)
  body=$(echo "$body" | sed '$d')
  echo "  $label: $status"
  if [ "$status" = "401" ] && echo "$body" | grep -q "$GATEWAY_401"; then
    echo "  FAIL: gateway blocked public route with JWT check"
    return 1
  fi
  return 0
}

check_public POST "/api/auth/register" '{"email":"t@t.com","password":"testpass8","name":"T"}' "POST /api/auth/register" || TEST2_OK=false
check_public POST "/api/auth/login" '{"email":"t@t.com","password":"testpass8"}' "POST /api/auth/login" || TEST2_OK=false
check_public POST "/api/auth/refresh" '{"refresh_token":"fake"}' "POST /api/auth/refresh" || TEST2_OK=false
check_public GET "/api/market/instruments" "" "GET /api/market/instruments" || TEST2_OK=false
check_public GET "/api/market/instruments/AAPL" "" "GET /api/market/instruments/AAPL" || TEST2_OK=false
check_public GET "/api/market/instruments/AAPL/price" "" "GET /api/market/instruments/AAPL/price" || TEST2_OK=false
check_public GET "/api/earnings/upcoming" "" "GET /api/earnings/upcoming" || TEST2_OK=false
check_public POST "/api/billing/webhook" '{}' "POST /api/billing/webhook" || TEST2_OK=false

if $TEST2_OK; then pass "TEST 2 — Public routes pass through gateway"; else fail "TEST 2 — Public routes" "gateway blocked a public route"; fi

# ============================================================================
# TEST 3 — Protected routes without token
# ============================================================================
echo ""
echo "========== TEST 3: Protected routes without token =========="
TEST3_OK=true
for endpoint in "/api/portfolio/portfolios" "/api/forecast/top-picks" "/api/news/feed"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" localhost:8000$endpoint)
  echo "  $endpoint: $STATUS"
  if [ "$STATUS" != "401" ]; then
    echo "  FAIL: expected 401, got $STATUS"
    TEST3_OK=false
  fi
done
if $TEST3_OK; then pass "TEST 3 — Protected routes"; else fail "TEST 3 — Protected routes" "expected 401"; fi

# ============================================================================
# TEST 4 — Invalid JWT
# ============================================================================
echo ""
echo "========== TEST 4: Invalid JWT =========="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/portfolio/portfolios \
  -H "Authorization: Bearer definitely.not.valid.jwt")
echo "  Invalid JWT: $STATUS"
if [ "$STATUS" = "401" ]; then pass "TEST 4 — Invalid JWT"; else fail "TEST 4 — Invalid JWT" "got $STATUS"; fi

# ============================================================================
# TEST 5 — CORS headers
# ============================================================================
echo ""
echo "========== TEST 5: CORS headers =========="
CORS=$(curl -s -D - -H "Origin: http://localhost:3000" localhost:8000/health 2>&1 | grep -i "access-control-allow-origin")
echo "  $CORS"
if echo "$CORS" | grep -qi "localhost:3000"; then
  pass "TEST 5 — CORS headers"
else
  fail "TEST 5 — CORS headers" "no access-control-allow-origin"
fi

# ============================================================================
# TEST 6 — Rate limiting
# ============================================================================
echo ""
echo "========== TEST 6: Rate limiting =========="
# Clear existing rate limit keys
$DOCKER exec predictamarket-redis redis-cli KEYS "rl:*" 2>/dev/null | while read key; do
  $DOCKER exec predictamarket-redis redis-cli DEL "$key" 2>/dev/null
done
sleep 1

RL_OUTPUT=$(cd "$PROJECT_ROOT" && .venv/bin/python tests/test_ratelimit.py 2>&1)
echo "$RL_OUTPUT"
if echo "$RL_OUTPUT" | grep -q "PASSED"; then
  pass "TEST 6 — Rate limiting"
else
  fail "TEST 6 — Rate limiting" "429 not triggered"
fi

# ============================================================================
# TEST 7 — Structlog JSON logs
# ============================================================================
echo ""
echo "========== TEST 7: Structlog JSON logs =========="
# Generate a fresh log entry
curl -s localhost:8000/health > /dev/null
sleep 1
LOG_LINE=$($COMPOSE logs api-gateway --tail=20 2>&1 | grep '"event": "request"' | tail -1)
echo "  $LOG_LINE"
if echo "$LOG_LINE" | grep -q '"method"' && echo "$LOG_LINE" | grep -q '"path"' && echo "$LOG_LINE" | grep -q '"status"'; then
  pass "TEST 7 — Structlog JSON logs"
else
  fail "TEST 7 — Structlog JSON logs" "missing required fields"
fi

# ============================================================================
# RESULTS
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
