"""
DAG: Fetch insider transactions for 94 tickers.
yfinance → PostgreSQL insider_transactions
Schedule: 08:00 ET daily, Mon-Fri.
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
    dag_id="dag_fetch_insider",
    default_args=default_args,
    description="Fetch insider transactions via yfinance",
    schedule="0 8 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market", "insider", "daily"],
) as dag:

    fetch_insider = BashOperator(
        task_id="fetch_insider",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-insider '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
