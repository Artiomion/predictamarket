"""
DAG: Airflow log cleanup — delete logs older than 30 days.
Schedule: every Sunday at 03:00.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_maintenance",
    default_args=default_args,
    description="Clean up Airflow logs older than 30 days",
    schedule="0 3 * * 0",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["maintenance", "cleanup"],
) as dag:

    cleanup_logs = BashOperator(
        task_id="cleanup_logs",
        bash_command=(
            "find /opt/airflow/logs -type f -mtime +30 ! -newermt '7 days ago' -delete "
            "&& echo 'Old logs cleaned'"
        ),
        execution_timeout=timedelta(minutes=10),
    )
