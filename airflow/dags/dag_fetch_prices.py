"""
DAG: Fetch OHLCV prices for 94 S&P 500 tickers.
yfinance → PostgreSQL price_history + Redis cache + PUBLISH price.updated
Schedule: every 15 min during US market hours (ET), Mon-Fri.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=15),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_prices",
    default_args=default_args,
    description="Fetch OHLCV prices for 94 tickers via yfinance",
    schedule="*/15 9-16 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market", "prices", "frequent"],
) as dag:

    fetch_prices = BashOperator(
        task_id="fetch_prices",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-prices '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
