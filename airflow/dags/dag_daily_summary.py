"""
DAG: End-of-day catch-all — ensure all data is fresh before market close.
Runs financials, earnings, batch forecast sequentially.
Schedule: 22:00 ET daily, Mon-Fri (after market close).
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
}

MARKET_URL = "http://market-data-service:8002/api/market"
FORECAST_URL = "http://forecast-service:8004/api/forecast"
CURL_AUTH = '-H "x-internal-key: $INTERNAL_API_KEY"'

with DAG(
    dag_id="dag_daily_summary",
    default_args=default_args,
    description="End-of-day catch-all: financials + earnings + forecast",
    schedule="0 22 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["summary", "daily", "evening"],
) as dag:

    update_financials = BashOperator(
        task_id="update_financials",
        bash_command=f'curl -sf -X POST {MARKET_URL}/admin/update-financials {CURL_AUTH}',
        execution_timeout=timedelta(minutes=30),
    )

    update_earnings = BashOperator(
        task_id="update_earnings",
        bash_command=f'curl -sf -X POST {MARKET_URL}/admin/update-earnings {CURL_AUTH}',
        execution_timeout=timedelta(minutes=15),
    )

    run_forecast = BashOperator(
        task_id="run_batch_forecast",
        bash_command=f'curl -sf -X POST {FORECAST_URL}/admin/run-batch {CURL_AUTH}',
        execution_timeout=timedelta(minutes=60),
    )

    update_financials >> update_earnings >> run_forecast
