"""
DAG: Fetch SEC EDGAR 10-Q/10-K filings for 94 tickers.
SEC EDGAR API → PostgreSQL filings, income_statements, balance_sheets, cash_flows
Schedule: 07:00 ET daily, Mon-Fri.
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
    dag_id="dag_fetch_edgar",
    default_args=default_args,
    description="Fetch SEC EDGAR 10-Q/10-K filings",
    schedule="0 7 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["edgar", "sec", "daily"],
) as dag:

    fetch_edgar = BashOperator(
        task_id="fetch_edgar",
        bash_command=(
            'curl -sf -X POST http://edgar-service:8007/api/edgar/admin/fetch-edgar '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
