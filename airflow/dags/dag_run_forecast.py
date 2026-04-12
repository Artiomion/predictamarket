"""
DAG: Run batch TFT forecast for all 94 tickers.
Waits for fresh prices + news, then triggers forecast-service batch inference.
Schedule: every hour during US market hours (ET), Mon-Fri.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_run_forecast",
    default_args=default_args,
    description="Run batch TFT forecast after fresh prices + news",
    schedule="0 10-16 * * 1-5",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["forecast", "ml", "heavy"],
) as dag:

    wait_prices = ExternalTaskSensor(
        task_id="wait_for_prices",
        external_dag_id="dag_fetch_prices",
        timeout=600,
        mode="reschedule",
        poke_interval=60,
    )

    wait_news = ExternalTaskSensor(
        task_id="wait_for_news",
        external_dag_id="dag_fetch_news",
        timeout=600,
        mode="reschedule",
        poke_interval=60,
    )

    run_forecast = BashOperator(
        task_id="run_batch_forecast",
        bash_command=(
            'curl -sf -X POST http://forecast-service:8004/api/forecast/admin/run-batch '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
        execution_timeout=timedelta(minutes=60),
    )

    [wait_prices, wait_news] >> run_forecast
