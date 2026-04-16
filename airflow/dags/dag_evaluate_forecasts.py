"""
DAG: Evaluate past forecasts against actual prices.
Populates forecast.forecast_history with accuracy metrics.
Schedule: 21:00 ET daily, Mon-Fri (after market data settles).
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=10),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_evaluate_forecasts",
    default_args=default_args,
    description="Evaluate forecast accuracy against actual prices",
    schedule="0 21 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["forecast", "accuracy", "daily"],
) as dag:

    evaluate = BashOperator(
        task_id="evaluate_forecasts",
        bash_command=(
            'curl -sf -X POST http://forecast-service:8004/api/forecast/admin/evaluate '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
