"""
DAG: Fetch earnings calendar and results for 94 tickers.
yfinance → PostgreSQL earnings_calendar, earnings_results
Schedule: 06:30 ET daily, Mon-Fri.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=15),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_earnings",
    default_args=default_args,
    description="Fetch earnings calendar and results via yfinance",
    schedule="30 6 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market", "earnings", "daily"],
) as dag:

    fetch_earnings = BashOperator(
        task_id="fetch_earnings",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-earnings '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
