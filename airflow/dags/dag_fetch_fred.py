"""
DAG: Fetch FRED macroeconomic series into market.macro_history.

Series populated:
  - cpi                  (CPIAUCSL, monthly)
  - unemployment         (UNRATE, monthly)
  - fed_funds_rate       (DFF, daily)
  - yield_curve_spread   (T10Y2Y, daily)
  - m2_money_supply      (M2SL, monthly)
  - wti_crude            (DCOILWTICO, daily)
  - fred_vix             (VIXCLS, daily)

Schedule: once per day at 06:30 ET (after market open prep, before
  dag_fetch_prices / dag_run_forecast). Monthly series update with 1–2 month lag,
  so daily is fine (forward-fill handles the rest).

Idempotent — re-running on same day updates existing rows.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "predictamarket",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_fred",
    default_args=default_args,
    description="Fetch FRED macro series (CPI, UNRATE, FedFunds, T10Y2Y, M2, WTI, VIX)",
    schedule="30 6 * * *",  # 06:30 ET daily
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["macro", "fred", "data-ingest"],
) as dag:

    fetch_fred = BashOperator(
        task_id="fetch_fred",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-fred '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
        execution_timeout=timedelta(minutes=5),
    )
