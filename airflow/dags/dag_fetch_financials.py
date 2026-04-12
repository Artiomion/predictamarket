"""
DAG: Fetch financial statements for 94 tickers.
yfinance → PostgreSQL financial_metrics
Schedule: 06:00 ET daily, Mon-Fri (before market open).
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=30),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_financials",
    default_args=default_args,
    description="Fetch financial statements for 94 tickers via yfinance",
    schedule="0 6 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market", "financials", "daily"],
) as dag:

    fetch_financials = BashOperator(
        task_id="fetch_financials",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-financials '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
