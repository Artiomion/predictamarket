# Ensemble / Alpha Signals — design notes

Living doc for decisions that aren't obvious from code alone.

## Memory budget (was #8 in code review)

Ensemble lazy-loads 3 TFT checkpoints (ep2, ep4, ep5). ep5 is also the primary
model so it's reused — net in-RAM footprint:

| Component | Size |
|---|---|
| Primary ep5 | ~188 MB |
| Ensemble ep2 | ~188 MB |
| Ensemble ep4 | ~188 MB |
| **Total TFT weights** | **~560 MB** |
| + FinBERT (optional) | ~440 MB |
| + Python/pandas runtime | ~300 MB |
| **forecast-service RSS** | **~1.1–1.3 GB** |

Docker memory limit: `3g`. Plenty of headroom.

**If we ever add a 4th ensemble member** (e.g., for walk-forward cross-validation
across training runs), budget grows linearly. At ~750 MB for weights alone the
limit is still fine, but heads-up.

## Why `ensemble_weights` is `DOUBLE PRECISION[]`, not `JSONB` (was #12)

Three reasons:
1. Array length is fixed (3) and element type is known → schema precision.
2. Sort/filter support: `ensemble_weights[1] > 0.5` is a valid SQL predicate;
   JSONB would need `->` casts every time.
3. Postgres-only stack; the project isn't building a DB-engine-agnostic ORM
   abstraction. Keep.

If we ever need a multi-engine story we'd migrate to JSONB with a single query.
Small scope, easy rollback.

## Race condition avoidance (was #2)

`run_alpha_signals.py` no longer runs the pattern
`UPDATE ... SET is_latest=false; INSERT ON CONFLICT DO UPDATE is_latest=true`
per-ticker. That had two failure modes:
1. Concurrent DAG runs could both step-1 then both step-2 → two "latest" rows.
2. Each ticker triggered two SQL round-trips.

Current behaviour:
- **Per-ticker:** single upsert (INSERT ... ON CONFLICT DO UPDATE). Unique index
  on `(ticker, forecast_date)` guarantees one row per ticker per day.
- **End-of-run cleanup:** one bulk
  `UPDATE WHERE forecast_date < CURRENT_DATE SET is_latest=false` — flips every
  older row stale in one statement.

Max `is_latest=true` rows per ticker ≤ 2 (today's + yesterday's mid-run),
converges to exactly 1 after cleanup.

## Airflow DAG wait pattern (was #11)

`dag_alpha_signals` uses two tasks after the trigger:
1. `trigger_alpha_signals` (BashOperator, curl → 202 in seconds)
2. `wait_alpha_complete` (BashSensor, polls `/admin/alpha-signals-status`
   every 120s until phase=`done`, 2h timeout)

The status endpoint reads Redis key `alpha_signals:status` that the script
updates every 25 tickers + on completion. This replaces the previous fire-and-forget
pattern which lied to Airflow (green immediately, actual work still running).

## Checkpoint pinning (was #7)

`model_loader.CKPT_SHA256` contains SHA256 of each ensemble checkpoint. On load,
we compute the hash and log a warning if it doesn't match. We do NOT refuse to
load — dev machines may have different files and blocking startup is worse than
a noisy warning. Alert on `ckpt_sha_mismatch` in production logs.

## Disagreement thresholds (was #15)

Live in `shared/utils.py`:
- `DISAGREEMENT_TIER_HIGH_MAX = 0.005`
- `DISAGREEMENT_TIER_MEDIUM_MAX = 0.016`

Derived from the ensemble_3_comparison study:
- p50 of `std(medians)/|mean|` ≈ 0.008
- p90 ≈ 0.016

After any retrain, re-run the comparison script and update these constants.
Recommended: bake into config.json with the model artifacts so they ship together.
