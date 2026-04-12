"""
DAG: Fetch macro indicators (VIX, S&P 500, DXY, gold, oil, treasury).
yfinance → PostgreSQL macro_history
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
    "execution_timeout": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_macro",
    default_args=default_args,
    description="Fetch macro indicators via yfinance",
    schedule="*/15 9-16 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["market", "macro", "frequent"],
) as dag:

    fetch_macro = BashOperator(
        task_id="fetch_macro",
        bash_command=(
            'curl -sf -X POST http://market-data-service:8002/api/market/admin/update-macro '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
